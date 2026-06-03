from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from uuid import uuid4

from ai.voice.qwen3_runtime import DEFAULT_OUTPUT_DIR
from ai.voice.tts import generate_tts
from ai.voice.clone import build_voice_clone_prompt, generate_voice_clone


# ── Preset voiceId → Qwen CustomVoice speaker name ────────────────────────────
QWEN_SPEAKER_BY_VOICE_ID: dict[str, str] = {
    "voice_preset_narrator_calm_001": "sohee",
    "voice_preset_narrator_bright_001": "serena",
    "voice_preset_narrator_soft_001": "vivian",
    "voice_preset_narrator_serious_001": "ryan",
}

# ── 캐시 레이어 1: voiceId → {"ref_audio": path/URL, "ref_text": str} ─────────
# 프로세스 재시작 시 초기화. cache miss 시 payload의 referenceAudioUrl/referenceText로 재구성.
_CLONE_REF_CACHE: dict[str, dict[str, str]] = {}

# ── 캐시 레이어 2: voiceId → List[VoiceClonePromptItem] ──────────────────────
# create_voice_clone_prompt() 결과 캐시 — 이 객체를 재사용하면 GPU 재추론 생략.
# VoiceClonePromptItem은 직렬화 불가능 → 프로세스 내 메모리만 유지.
# cache miss 시 레이어1에서 ref_audio/ref_text를 꺼내 재구성.
_CLONE_PROMPT_CACHE: dict[str, list] = {}

# ── Storage root: /storage/... 상대 URL → 로컬 파일 경로 변환용 ───────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_STORAGE_ROOT = _PROJECT_ROOT / "backend" / "app" / "storage"


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _storage_url_for(path: str, public_base_url: str | None = None) -> str:
    """절대 파일 경로 → /storage URL 또는 public 절대 URL 변환."""
    audio_path = Path(path).resolve()
    try:
        relative = audio_path.relative_to(_STORAGE_ROOT)
        storage_url = f"/storage/{relative.as_posix()}"
    except ValueError:
        storage_url = f"/storage/audio/{audio_path.name}"
    if public_base_url:
        return urljoin(f"{public_base_url.rstrip('/')}/", storage_url.lstrip("/"))
    return storage_url


def _backend_base_url() -> str | None:
    return (
        os.getenv("BACKEND_PUBLIC_BASE_URL")
        or os.getenv("AI_TTS_BACKEND_BASE_URL")
        or None
    )


def _resolve_reference_audio(reference_audio_url: str) -> str:
    """referenceAudioUrl을 generate_voice_clone()이 사용할 수 있는 경로/URL로 변환.

    1. http/https: 그대로 반환
    2. /storage/...: 로컬 파일 경로 시도 → 실패하면 BACKEND_PUBLIC_BASE_URL 조합
    3. 모두 실패: ValueError (silent sohee fallback 없음)
    """
    parsed = urlparse(reference_audio_url)
    if parsed.scheme in {"http", "https"}:
        return reference_audio_url

    if reference_audio_url.startswith("/storage/"):
        relative = reference_audio_url[len("/storage/"):]
        local_path = _STORAGE_ROOT / relative
        if local_path.is_file():
            return str(local_path)

        base = _backend_base_url()
        if base:
            return f"{base.rstrip('/')}{reference_audio_url}"

        raise ValueError(
            f"referenceAudioUrl='{reference_audio_url}' 해석 실패: "
            f"로컬 파일 없음({local_path}), "
            f"BACKEND_PUBLIC_BASE_URL/AI_TTS_BACKEND_BASE_URL 미설정."
        )

    raise ValueError(
        f"지원하지 않는 referenceAudioUrl 형식: '{reference_audio_url}'. "
        f"http(s):// 또는 /storage/... 형식이어야 합니다."
    )


def _instruction_for(item: dict[str, Any]) -> str | None:
    """voicePrompt + characterPrompt + emotionPrompt 조합 instruction 빌드.

    Note: 0.6B CustomVoice 모델은 instruct를 내부적으로 None 처리함.
    presest 합성에서는 사용되지만 실제 반영 여부는 모델 크기에 달려 있다.
    clone 합성(Base 모델)에는 현재 전달하지 않는다.
    """
    parts: list[str] = []
    if vp := (item.get("voicePrompt") or "").strip():
        parts.append(f"Voice style: {vp}")
    elif vn := (item.get("voiceName") or "").strip():
        parts.append(f"Voice style: {vn}")
    if cp := (item.get("characterPrompt") or "").strip():
        parts.append(f"Character style: {cp}")
    if ep := (item.get("emotionPrompt") or "").strip():
        parts.append(ep)
    elif em := (item.get("emotion") or item.get("emotionLabel") or "").strip():
        parts.append(f"Emotion: {em}")
    return ". ".join(parts) if parts else None


def _get_clone_ref(item: dict[str, Any]) -> dict[str, str]:
    """레이어1 캐시에서 ref_audio/ref_text를 조회하거나 payload에서 구성.

    Returns {"ref_audio": str, "ref_text": str}
    Raises ValueError: 캐시 없음 + referenceAudioUrl/referenceText 누락
    """
    voice_id = (item.get("voiceId") or "").strip()

    if voice_id and voice_id in _CLONE_REF_CACHE:
        return _CLONE_REF_CACHE[voice_id]

    ref_url = (item.get("referenceAudioUrl") or "").strip()
    ref_text = (item.get("referenceText") or "").strip()

    if not ref_url or not ref_text:
        raise ValueError(
            f"Clone voiceId='{voice_id}': 레이어1 캐시 없음 + "
            f"referenceAudioUrl/referenceText 누락. "
            f"백엔드가 TTS payload에 이 값을 반드시 포함해야 합니다."
        )

    ref_audio = _resolve_reference_audio(ref_url)
    entry: dict[str, str] = {"ref_audio": ref_audio, "ref_text": ref_text}
    if voice_id:
        _CLONE_REF_CACHE[voice_id] = entry
    return entry


def _get_clone_prompt(voice_id: str, ref_audio: str, ref_text: str) -> list:
    """레이어2 캐시에서 VoiceClonePromptItem을 조회하거나 새로 빌드.

    캐시 히트: 저장된 prompt 반환 (GPU 재추론 없음)
    캐시 미스: build_voice_clone_prompt() 호출 후 캐시 저장
    """
    if voice_id and voice_id in _CLONE_PROMPT_CACHE:
        return _CLONE_PROMPT_CACHE[voice_id]

    prompt = build_voice_clone_prompt(ref_audio, ref_text)
    if voice_id:
        _CLONE_PROMPT_CACHE[voice_id] = prompt
    return prompt


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def store_clone_cache(
    voice_id: str,
    ref_audio_path: str,
    ref_text: str,
    voice_clone_prompt: list | None = None,
) -> None:
    """/clone endpoint 완료 후 두 레이어 캐시를 모두 업데이트한다.

    voice_clone_prompt가 제공되면 레이어2까지 채워 이후 /tts 합성이 즉시 빠른 경로를 탄다.
    """
    _CLONE_REF_CACHE[voice_id] = {"ref_audio": ref_audio_path, "ref_text": ref_text}
    if voice_clone_prompt is not None:
        _CLONE_PROMPT_CACHE[voice_id] = voice_clone_prompt


def synthesize_scene_tts(
    payload: dict[str, Any],
    *,
    public_base_url: str | None = None,
) -> dict[str, Any]:
    """TTS_AI_CONTRACT.md AI/TTS 측 구현체.

    Input:
        { storyId, sceneId, items: [{ audioId, text, voiceId,
          referenceAudioUrl, referenceText, emotionPrompt, characterPrompt, ... }] }
    Output:
        { storyId, sceneId, audios: [{ audioId, audioUrl, durationSec, error }] }

    voiceId 처리:
    - QWEN_SPEAKER_BY_VOICE_ID 에 있음 → preset: CustomVoice 모델 + 고정 speaker
    - 없음 → clone: Base 모델 + VoiceClonePromptItem 캐시(레이어2) 우선,
              없으면 ref_audio/ref_text(레이어1) → prompt 빌드 → 캐시 저장
    - clone인데 reference 없고 캐시도 없음 → item error (전체 scene 실패 아님)
    """
    audios: list[dict[str, Any]] = []

    for item in payload.get("items", []):
        audio_id = item.get("audioId")
        text = (item.get("text") or "").strip()

        if not audio_id:
            continue

        if not text:
            audios.append({
                "audioId": audio_id,
                "audioUrl": None,
                "durationSec": None,
                "error": "Text is empty.",
            })
            continue

        try:
            voice_id = (item.get("voiceId") or "").strip()
            instruction = _instruction_for(item)

            if voice_id in QWEN_SPEAKER_BY_VOICE_ID:
                # ── Preset narrator: CustomVoice 모델 + 고정 speaker ────────
                result = generate_tts(
                    text,
                    speaker=QWEN_SPEAKER_BY_VOICE_ID[voice_id],
                    language="Korean",
                    instruct=instruction,  # 0.6B 모델에서 내부적으로 None 처리
                )

            else:
                # ── Clone voice: Base 모델 + VoiceClonePromptItem 캐시 ──────
                # sohee fallback 금지 — reference 없고 캐시도 없으면 item error

                # 레이어2 캐시 확인 (VoiceClonePromptItem 객체)
                if voice_id and voice_id in _CLONE_PROMPT_CACHE:
                    prompt = _CLONE_PROMPT_CACHE[voice_id]
                    result = generate_voice_clone(
                        text,
                        voice_clone_prompt=prompt,
                        language="Korean",
                    )
                else:
                    # 레이어1 캐시 또는 payload에서 ref 정보 획득
                    ref = _get_clone_ref(item)
                    # prompt 빌드 + 레이어2 캐시 저장
                    prompt = _get_clone_prompt(voice_id, ref["ref_audio"], ref["ref_text"])
                    result = generate_voice_clone(
                        text,
                        voice_clone_prompt=prompt,
                        language="Korean",
                    )

            audios.append({
                "audioId": audio_id,
                "audioUrl": _storage_url_for(result["audio_path"], public_base_url),
                "durationSec": result.get("duration_sec"),
                "error": None,
            })

        except Exception as exc:  # noqa: BLE001 — item 단위 실패 허용
            audios.append({
                "audioId": audio_id,
                "audioUrl": None,
                "durationSec": None,
                "error": str(exc),
            })

    return {
        "storyId": payload.get("storyId"),
        "sceneId": payload.get("sceneId"),
        "audios": audios,
    }

from __future__ import annotations

import base64
import io
import importlib.util
import math
import os
from pathlib import Path
import struct
from typing import Any
import urllib.parse
import wave

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
import httpx

from ai.voice.comfy_tts import (
    TTS_OUTPUT_DIR_ENV,
    health_check as comfy_tts_health_check,
    synthesize_scene_tts_via_comfy,
)

MOCK_ENV = "TTS_ADAPTER_MOCK"
QWEN_ENV = "TTS_ADAPTER_QWEN"  # TTS_ADAPTER_QWEN=1 → /tts에서 Qwen 직접 사용

# voiceId별 reference 오디오 저장 기본 디렉토리 (clone endpoint 전용)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_CLONE_STORAGE_DIR = _PROJECT_ROOT / ".cache" / "qwen3_tts" / "voices"

app = FastAPI(
    title="Mongsil TTS Adapter",
    description="Remote AI_TTS_URL + AI_VOICE_CLONE_URL server. Supports ComfyUI, Qwen3-TTS, and mock modes.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_ALLOWED_AUDIO_EXTS = {"webm", "wav", "mp3", "m4a", "ogg", "flac"}
_EXT_FROM_MIME = {
    "audio/webm": "webm",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "m4a",
    "audio/x-m4a": "m4a",
    "audio/aac": "m4a",
    "audio/ogg": "ogg",
    "audio/flac": "flac",
}


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _tts_output_dir() -> Path | None:
    output_dir = os.getenv(TTS_OUTPUT_DIR_ENV)
    if not output_dir:
        return None
    return Path(output_dir).expanduser().resolve()


def _public_base_url(request: Request) -> str:
    configured = os.getenv("AI_TTS_PUBLIC_BASE_URL")
    if configured:
        return configured.rstrip("/")
    return str(request.base_url).rstrip("/")


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _enabled(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _mock_enabled() -> bool:
    return _enabled(os.getenv(MOCK_ENV))


def _qwen_enabled() -> bool:
    return _enabled(os.getenv(QWEN_ENV))


def _mock_audio_url(public_base_url: str, audio_id: str) -> str:
    quoted = urllib.parse.quote(audio_id)
    return f"{public_base_url.rstrip('/')}/mock-audio/{quoted}.wav"


def _mock_tts_response(payload: dict[str, Any], public_base_url: str) -> dict[str, Any]:
    audios = []
    for item in payload.get("items", []):
        audio_id = item.get("audioId")
        if not audio_id:
            continue
        text = (item.get("text") or "").strip()
        audios.append({
            "audioId": audio_id,
            "audioUrl": _mock_audio_url(public_base_url, audio_id) if text else None,
            "durationSec": 0.8 if text else None,
            "error": None if text else "Text is empty.",
        })
    return {
        "storyId": payload.get("storyId"),
        "sceneId": payload.get("sceneId"),
        "audios": audios,
    }


def _voice_sample_tts_payload(payload: dict[str, Any]) -> dict[str, Any]:
    voice_id = payload.get("voiceId") or "voice_sample"
    sample_text = payload.get("sampleText") or payload.get("text") or "안녕하세요. 저는 이 목소리로 동화를 들려드릴게요."
    audio_id = f"sample_{voice_id}"
    return {
        "storyId": "voice_sample",
        "sceneId": f"voice_sample_{voice_id}",
        "items": [
            {
                "audioId": audio_id,
                "itemIndex": 0,
                "type": "narration",
                "speaker": None,
                "text": sample_text,
                "emotion": "calm",
                "emotionLabel": "샘플",
                "voiceType": payload.get("voiceType") or "narrator",
                "voiceId": voice_id,
                "voiceName": payload.get("voiceName"),
                "voicePrompt": payload.get("voicePrompt"),
                "emotionPrompt": payload.get("emotionPrompt") or "Speak in a clear, natural narrator sample voice.",
                "characterPrompt": payload.get("characterPrompt"),
                "referenceAudioUrl": payload.get("referenceAudioUrl"),
                "referenceText": payload.get("referenceText"),
            }
        ],
    }


def _voice_sample_response(result: dict[str, Any]) -> dict[str, Any]:
    audios = result.get("audios") or []
    audio = audios[0] if audios else {}
    return {
        "audioUrl": audio.get("audioUrl"),
        "durationSec": audio.get("durationSec"),
        "error": audio.get("error"),
        "provider": "qwen" if _qwen_enabled() else "comfyui",
        "model": "Qwen3-TTS-12Hz-0.6B" if _qwen_enabled() else "qwen3-tts-adapter",
    }


def _mock_wav_bytes(audio_id: str) -> bytes:
    sample_rate = 16000
    duration_seconds = 0.8
    frequency = 420 + (sum(audio_id.encode("utf-8")) % 220)
    frame_count = int(sample_rate * duration_seconds)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for index in range(frame_count):
            t = index / sample_rate
            envelope = min(1.0, index / 1200, (frame_count - index) / 1200)
            value = int(9000 * envelope * math.sin(2 * math.pi * frequency * t))
            wav.writeframesraw(struct.pack("<h", value))
    return buffer.getvalue()


def _ext_from_filename(filename: str | None) -> str:
    if filename and "." in filename:
        ext = filename.rsplit(".", 1)[1].lower()
        if ext in _ALLOWED_AUDIO_EXTS:
            return ext
    return "webm"


def _wav_bytes_to_base64(path: str) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def _wav_duration_sec(path: str) -> float | None:
    try:
        with wave.open(path, "rb") as wf:
            return round(wf.getnframes() / wf.getframerate(), 3)
    except Exception:  # noqa: BLE001
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/")
def root() -> dict[str, Any]:
    mode = "mock" if _mock_enabled() else ("qwen" if _qwen_enabled() else "comfy")
    return {
        "service": "mongsil-tts-adapter",
        "status": "running",
        "mode": mode,
        "health": "/health",
        "tts": "/tts",
        "clone": "/clone",
        "voiceSample": "/voice-sample",
    }


@app.get("/health")
def health(request: Request) -> dict[str, Any]:
    public_base_url = _public_base_url(request)
    mock_enabled = _mock_enabled()
    qwen_enabled = _qwen_enabled()
    if mock_enabled:
        comfy = {"ok": True, "mock": True}
    elif qwen_enabled:
        comfy = {"ok": True, "mode": "qwen", "note": "Qwen3-TTS direct mode; ComfyUI not used"}
    else:
        comfy = comfy_tts_health_check()
    return {
        "ok": bool(comfy.get("ok")),
        "service": "mongsil-tts-adapter",
        "mode": "mock" if mock_enabled else ("qwen" if qwen_enabled else "comfy"),
        "mockEnabled": mock_enabled,
        "qwenEnabled": qwen_enabled,
        "publicBaseUrl": public_base_url,
        "comfy": comfy,
        "fastapiInstalled": _module_available("fastapi"),
        "httpxInstalled": _module_available("httpx"),
    }


@app.post("/tts")
async def tts(request: Request) -> dict[str, Any]:
    payload = await request.json()

    if _mock_enabled():
        return _mock_tts_response(payload, _public_base_url(request))

    if _qwen_enabled():
        # Qwen 직접 합성 (QWEN TTS_ADAPTER_QWEN=1)
        from ai.voice.tts_contract import synthesize_scene_tts
        return synthesize_scene_tts(payload, public_base_url=_public_base_url(request))

    return synthesize_scene_tts_via_comfy(payload, public_base_url=_public_base_url(request))


@app.post("/clone")
async def clone_voice_endpoint(
    audioFile: UploadFile = File(...),
    voiceId: str = Form(...),
    referenceText: str = Form(...),
    sampleText: str = Form("이 목소리는 동화 속 캐릭터 대사에 사용됩니다."),
    voiceType: str = Form("character"),
    voicePrompt: str = Form(""),
    characterId: str = Form(""),
    language: str = Form("Korean"),
    provider: str = Form("qwen"),
    model: str = Form("Qwen3-TTS-12Hz-0.6B-Base"),
) -> dict[str, Any]:
    """보이스 클로닝 endpoint.

    백엔드가 reference 오디오 bytes를 multipart로 전송하면:
    1. 오디오를 storage/voices/{voiceId}/ 에 저장 (로컬에 있으면 스킵)
    2. generate_voice_clone()으로 sampleText 합성
    3. voiceId 기준 캐시 업데이트
    4. JSON { sampleAudioBase64, durationSec, provider, model } 반환

    mock 모드에서는 mock wav bytes를 반환한다.
    """
    if _mock_enabled():
        mock_bytes = _mock_wav_bytes(f"clone_{voiceId}")
        return {
            "sampleAudioBase64": base64.b64encode(mock_bytes).decode("ascii"),
            "mimeType": "audio/wav",
            "durationSec": 0.8,
            "provider": "mock",
            "model": "mock",
        }

    from ai.voice.clone import build_voice_clone_prompt, generate_voice_clone
    from ai.voice.tts_contract import store_clone_cache
    # ── 1. reference 오디오 저장 ─────────────────────────────────────────
    audio_bytes = await audioFile.read()
    if not audio_bytes:
        return {"error": "audioFile is empty.", "sampleAudioBase64": None}

    ext = _ext_from_filename(audioFile.filename)
    ref_dir = _CLONE_STORAGE_DIR / voiceId
    ref_dir.mkdir(parents=True, exist_ok=True)
    ref_path = ref_dir / f"reference.{ext}"
    ref_path.write_bytes(audio_bytes)

    # ── 2. VoiceClonePromptItem 빌드 (GPU 추론 — 캐시에 저장) ────────────
    try:
        voice_clone_prompt = build_voice_clone_prompt(
            str(ref_path),
            referenceText or None,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "error": f"Clone prompt 빌드 실패: {exc}",
            "sampleAudioBase64": None,
            "durationSec": None,
            "provider": provider,
            "model": model,
        }

    # ── 3. 캐시 업데이트 (레이어1 + 레이어2) ─────────────────────────────
    store_clone_cache(voiceId, str(ref_path), referenceText, voice_clone_prompt)

    # ── 4. sampleText로 미리듣기 합성 (prompt 재사용 → 빠른 경로) ─────────
    try:
        result = generate_voice_clone(
            sampleText,
            voice_clone_prompt=voice_clone_prompt,
            language=language,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "error": f"Clone 합성 실패: {exc}",
            "sampleAudioBase64": None,
            "durationSec": None,
            "provider": provider,
            "model": model,
        }

    # ── 4. sample audio base64 반환 ───────────────────────────────────────
    sample_b64 = base64.b64encode(result["audio_bytes"]).decode("ascii")
    duration = result.get("duration_sec")

    return {
        "sampleAudioBase64": sample_b64,
        "mimeType": result.get("mime_type") or "audio/wav",
        "durationSec": duration,
        "provider": result.get("provider") or provider,
        "model": result.get("model") or model,
    }


@app.post("/voice-sample")
async def voice_sample(request: Request) -> dict[str, Any]:
    payload = _voice_sample_tts_payload(await request.json())
    if _mock_enabled():
        result = _mock_tts_response(payload, _public_base_url(request))
    elif _qwen_enabled():
        from ai.voice.tts_contract import synthesize_scene_tts
        result = synthesize_scene_tts(payload, public_base_url=_public_base_url(request))
    else:
        result = synthesize_scene_tts_via_comfy(payload, public_base_url=_public_base_url(request))
    return _voice_sample_response(result)


@app.get("/view")
def proxy_comfy_view(filename: str, subfolder: str = "", type: str = "output") -> Response:
    base_url = os.getenv("COMFYUI_VOICE_URL", "").rstrip("/")
    if not base_url:
        return Response("COMFYUI_VOICE_URL is not configured", status_code=500)
    try:
        response = httpx.get(
            f"{base_url}/view",
            params={"filename": filename, "subfolder": subfolder, "type": type},
            timeout=120,
        )
    except httpx.RequestError as exc:
        return Response(f"Failed to proxy ComfyUI /view: {exc}", status_code=502)
    if response.status_code != 200:
        return Response(response.text, status_code=response.status_code)
    return Response(
        content=response.content,
        media_type=response.headers.get("content-type", "audio/wav"),
    )


@app.get("/mock-audio/{audio_id}.wav")
def serve_mock_audio(audio_id: str) -> Response:
    return Response(content=_mock_wav_bytes(audio_id), media_type="audio/wav")


@app.get("/tts-output/{filename}")
def serve_tts_output(filename: str):
    output_dir = _tts_output_dir()
    if output_dir is None:
        return Response(f"{TTS_OUTPUT_DIR_ENV} is not configured", status_code=404)
    target = (output_dir / filename).resolve()
    if output_dir not in target.parents or not target.is_file():
        return Response("Audio file not found", status_code=404)
    return FileResponse(target, media_type="audio/wav")

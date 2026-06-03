from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from ai.voice.qwen3_runtime import (
    DEFAULT_CLONE_MODEL,
    DEFAULT_OUTPUT_DIR,
    load_qwen3_model,
    save_wav,
    select_device,
)


@lru_cache(maxsize=2)
def _get_clone_model(model_id: str, device: str):
    return load_qwen3_model(model_id, device)


def build_voice_clone_prompt(
    ref_audio: str,
    ref_text: str | None = None,
    *,
    model_id: str = DEFAULT_CLONE_MODEL,
    device: str = "auto",
) -> list:
    """Reference 오디오에서 VoiceClonePromptItem 목록을 빌드한다 (캐시용).

    이 호출이 GPU 추론의 무거운 부분이다 — 결과를 voiceId 기준으로 캐시하고
    이후 generate_voice_clone(voice_clone_prompt=cached)로 재사용한다.

    Returns: List[VoiceClonePromptItem]
    """
    resolved_device = select_device(device)
    model = _get_clone_model(model_id, resolved_device)
    return model.create_voice_clone_prompt(ref_audio=ref_audio, ref_text=ref_text)


def generate_voice_clone(
    text: str,
    *,
    ref_audio: str | None = None,
    ref_text: str | None = None,
    voice_clone_prompt: list | None = None,
    language: str = "Korean",
    output_path: str | Path | None = None,
    model_id: str = DEFAULT_CLONE_MODEL,
    device: str = "auto",
) -> dict:
    """클론 보이스로 음성을 합성한다.

    두 가지 경로:
    1. voice_clone_prompt 제공(캐시 히트) → 빠른 경로. prompt 빌드 생략.
    2. ref_audio + ref_text 제공(캐시 미스) → 내부에서 prompt 빌드 후 합성.

    Note: 0.6B Base 모델은 instruct/emotionPrompt를 지원하지 않는다.
    감정/말투 반영은 CustomVoice 모델(generate_tts) 전용이다.
    """
    if voice_clone_prompt is None and ref_audio is None:
        raise ValueError("voice_clone_prompt 또는 ref_audio 중 하나는 반드시 제공해야 합니다.")

    if voice_clone_prompt is None:
        parsed = urlparse(ref_audio)
        if parsed.scheme not in {"http", "https", "data"} and not Path(ref_audio).exists():
            raise FileNotFoundError(f"Reference audio 파일을 찾을 수 없습니다: {ref_audio}")

    resolved_device = select_device(device)
    model = _get_clone_model(model_id, resolved_device)

    if voice_clone_prompt is not None:
        # 캐시 히트 — 이미 빌드된 prompt로 바로 합성
        wavs, sample_rate = model.generate_voice_clone(
            text=text,
            language=language,
            voice_clone_prompt=voice_clone_prompt,
        )
    else:
        # 캐시 미스 — ref_audio/ref_text로 합성 (내부에서 prompt 빌드)
        wavs, sample_rate = model.generate_voice_clone(
            text=text,
            language=language,
            ref_audio=ref_audio,
            ref_text=ref_text,
        )

    wav = wavs[0]
    path = Path(output_path) if output_path else DEFAULT_OUTPUT_DIR / f"clone_{uuid4().hex}.wav"
    save_wav(path, wav, sample_rate)

    return {
        "audio_path": str(path),
        "sample_rate": sample_rate,
        "duration_sec": round(len(wav) / sample_rate, 3),
        "language": language,
        "model_id": model_id,
        "ref_audio": ref_audio,
    }

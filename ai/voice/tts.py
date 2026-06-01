from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from ai.voice.qwen3_runtime import (
    DEFAULT_CUSTOM_VOICE_MODEL,
    DEFAULT_OUTPUT_DIR,
    load_qwen3_model,
    save_wav,
    select_device,
)


@lru_cache(maxsize=2)
def _get_custom_voice_model(model_id: str, device: str):
    return load_qwen3_model(model_id, device)


def generate_tts(
    text: str,
    *,
    speaker: str = "Sohee",
    language: str = "Korean",
    instruct: str | None = None,
    output_path: str | Path | None = None,
    model_id: str = DEFAULT_CUSTOM_VOICE_MODEL,
    device: str = "auto",
) -> dict:
    resolved_device = select_device(device)
    model = _get_custom_voice_model(model_id, resolved_device)

    wavs, sample_rate = model.generate_custom_voice(
        text=text,
        language=language,
        speaker=speaker,
        instruct=instruct or None,
    )

    wav = wavs[0]
    path = Path(output_path) if output_path else DEFAULT_OUTPUT_DIR / f"tts_{uuid4().hex}.wav"
    save_wav(path, wav, sample_rate)

    return {
        "audio_path": str(path),
        "sample_rate": sample_rate,
        "duration_sec": round(len(wav) / sample_rate, 3),
        "speaker": speaker,
        "language": language,
        "model_id": model_id,
    }

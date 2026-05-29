from __future__ import annotations

from functools import lru_cache
from pathlib import Path
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


def generate_voice_clone(
    text: str,
    *,
    ref_audio: str,
    ref_text: str,
    language: str = "Korean",
    output_path: str | Path | None = None,
    model_id: str = DEFAULT_CLONE_MODEL,
    device: str = "auto",
) -> dict:
    parsed = urlparse(ref_audio)
    if parsed.scheme not in {"http", "https", "data"} and not Path(ref_audio).exists():
        raise FileNotFoundError(f"Reference audio file was not found: {ref_audio}")

    resolved_device = select_device(device)
    model = _get_clone_model(model_id, resolved_device)

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

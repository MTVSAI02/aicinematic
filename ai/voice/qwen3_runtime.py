from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import soundfile as sf
import torch

if TYPE_CHECKING:
    from qwen_tts import Qwen3TTSModel


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CUSTOM_VOICE_MODEL = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
DEFAULT_CLONE_MODEL = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "backend" / "app" / "storage" / "voice"
DEFAULT_NUMBA_CACHE_DIR = PROJECT_ROOT / ".cache" / "qwen3_tts" / "numba"


def configure_local_model_cache() -> None:
    """Configure Hugging Face runtime options used by local smoke-test scripts."""
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    DEFAULT_NUMBA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("NUMBA_CACHE_DIR", str(DEFAULT_NUMBA_CACHE_DIR))


def select_device(device: str) -> str:
    if device != "auto":
        return device

    return "cuda:0" if torch.cuda.is_available() else "cpu"


def dtype_for_device(device: str) -> torch.dtype:
    return torch.bfloat16 if device.startswith("cuda") else torch.float32


def resolve_model_source(model_id: str) -> str:
    model_path = Path(model_id)
    if model_path.exists():
        return str(model_path)

    try:
        from huggingface_hub import snapshot_download

        return snapshot_download(model_id, local_files_only=True)
    except Exception:
        return model_id


def load_qwen3_model(model_id: str, device: str) -> "Qwen3TTSModel":
    configure_local_model_cache()
    from qwen_tts import Qwen3TTSModel

    model_source = resolve_model_source(model_id)
    return Qwen3TTSModel.from_pretrained(
        model_source,
        device_map=device,
        dtype=dtype_for_device(device),
        attn_implementation="sdpa",
    )


def save_wav(output_path: Path, wav, sample_rate: int) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), wav, sample_rate)
    return output_path

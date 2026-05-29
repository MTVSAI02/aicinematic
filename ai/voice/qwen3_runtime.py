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


def configure_local_model_cache() -> None:
    """Configure Hugging Face runtime options used by local smoke-test scripts."""
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


def select_device(device: str) -> str:
    if device != "auto":
        return device

    return "cuda:0" if torch.cuda.is_available() else "cpu"


def dtype_for_device(device: str) -> torch.dtype:
    return torch.bfloat16 if device.startswith("cuda") else torch.float32


def load_qwen3_model(model_id: str, device: str) -> "Qwen3TTSModel":
    configure_local_model_cache()
    from qwen_tts import Qwen3TTSModel

    return Qwen3TTSModel.from_pretrained(
        model_id,
        device_map=device,
        dtype=dtype_for_device(device),
        attn_implementation="sdpa",
    )


def save_wav(output_path: Path, wav, sample_rate: int) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), wav, sample_rate)
    return output_path

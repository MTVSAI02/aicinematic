from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import urlparse

from qwen3_runtime import (
    DEFAULT_CLONE_MODEL,
    DEFAULT_OUTPUT_DIR,
    load_qwen3_model,
    save_wav,
    select_device,
)


DEFAULT_TEXT = "이 목소리는 캐릭터 라이브러리에 저장되어 다른 이야기에서도 재사용됩니다."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Qwen3-TTS voice-clone smoke-test WAV."
    )
    parser.add_argument("--ref-audio", required=True, help="Reference voice WAV/MP3 path.")
    parser.add_argument("--ref-text", required=True, help="Transcript of the reference audio.")
    parser.add_argument("--text", default=DEFAULT_TEXT)
    parser.add_argument("--language", default="Korean")
    parser.add_argument("--model", default=DEFAULT_CLONE_MODEL)
    parser.add_argument("--device", default="auto")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "qwen3_tts_voice_clone.wav",
    )
    return parser.parse_args()


def resolve_ref_audio(ref_audio: str) -> str:
    parsed = urlparse(ref_audio)
    if parsed.scheme in {"http", "https", "data"}:
        return ref_audio

    ref_audio_path = Path(ref_audio).expanduser()
    if not ref_audio_path.exists():
        raise SystemExit(
            "[qwen3-clone] reference audio file was not found.\n"
            f"[qwen3-clone] given path: {ref_audio}\n"
            "[qwen3-clone] Put a real WAV/MP3 file there, or pass an existing file path."
        )

    return str(ref_audio_path.resolve())


def main() -> None:
    args = parse_args()
    device = select_device(args.device)
    ref_audio = resolve_ref_audio(args.ref_audio)

    print(f"[qwen3-clone] loading model: {args.model}")
    print(f"[qwen3-clone] device: {device}")
    model = load_qwen3_model(args.model, device)

    print("[qwen3-clone] generating cloned audio...")
    wavs, sample_rate = model.generate_voice_clone(
        text=args.text,
        language=args.language,
        ref_audio=ref_audio,
        ref_text=args.ref_text,
    )

    output_path = save_wav(args.output, wavs[0], sample_rate)
    print(f"[qwen3-clone] saved: {output_path}")
    print(f"[qwen3-clone] sample_rate: {sample_rate}")


if __name__ == "__main__":
    main()

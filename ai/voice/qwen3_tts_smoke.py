from __future__ import annotations

import argparse
from pathlib import Path

from qwen3_runtime import (
    DEFAULT_CUSTOM_VOICE_MODEL,
    DEFAULT_OUTPUT_DIR,
    load_qwen3_model,
    save_wav,
    select_device,
)


DEFAULT_TEXT = (
    "안녕하세요. 내가 만든 캐릭터로 시리즈를 만드는 "
    "AI 시네마틱 데모입니다."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Korean Qwen3-TTS custom voice smoke-test WAV."
    )
    parser.add_argument("--text", default=DEFAULT_TEXT)
    parser.add_argument("--speaker", default="Sohee")
    parser.add_argument("--language", default="Korean")
    parser.add_argument("--instruct", default="")
    parser.add_argument("--model", default=DEFAULT_CUSTOM_VOICE_MODEL)
    parser.add_argument("--device", default="auto")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "qwen3_tts_custom_voice.wav",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    device = select_device(args.device)

    print(f"[qwen3-tts] loading model: {args.model}")
    print(f"[qwen3-tts] device: {device}")
    model = load_qwen3_model(args.model, device)

    print("[qwen3-tts] generating audio...")
    wavs, sample_rate = model.generate_custom_voice(
        text=args.text,
        language=args.language,
        speaker=args.speaker,
        instruct=args.instruct or None,
    )

    output_path = save_wav(args.output, wavs[0], sample_rate)
    print(f"[qwen3-tts] saved: {output_path}")
    print(f"[qwen3-tts] sample_rate: {sample_rate}")


if __name__ == "__main__":
    main()

"""Preset narrator sample WAV generation script.

Usage:
    python -m ai.voice.generate_preset_samples            # skip if file exists
    python -m ai.voice.generate_preset_samples --overwrite # always regenerate

Output:
    backend/app/storage/voices/{voiceId}/sample.wav (4 files)

Run environment:
    Requires venv with qwen_tts, torch, soundfile.
    Current shared PC path:
        C:\\Users\\WOO\\Documents\\Codex\\comfyui-tts\\.venv\\Scripts\\python.exe

Run command (from project root):
    & "C:\\Users\\WOO\\Documents\\Codex\\comfyui-tts\\.venv\\Scripts\\python.exe" `
        -m ai.voice.generate_preset_samples
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

SAMPLE_TEXT = "안녕하세요. 저는 이 목소리로 동화를 들려드릴게요."

PRESET_VOICES: list[tuple[str, str, str]] = [
    ("voice_preset_narrator_calm_001",    "sohee",  "calm"),
    ("voice_preset_narrator_bright_001",  "serena", "bright"),
    ("voice_preset_narrator_soft_001",    "vivian", "soft"),
    ("voice_preset_narrator_serious_001", "ryan",   "serious"),
]

_STORAGE_ROOT = _PROJECT_ROOT / "backend" / "app" / "storage"
_VOICE_STORAGE_DIR = _STORAGE_ROOT / "voices"


def _looks_like_audio_file(path: Path) -> bool:
    try:
        header = path.read_bytes()[:16]
    except OSError:
        return False
    return (
        (header.startswith(b"RIFF") and header[8:12] == b"WAVE")
        or header.startswith(b"ID3")
        or header.startswith(b"OggS")
        or header.startswith(b"fLaC")
    )


def generate_all(*, overwrite: bool = False) -> None:
    from ai.voice.tts import generate_tts

    print(f"[preset-samples] storage: {_VOICE_STORAGE_DIR}")
    print(f"[preset-samples] overwrite: {overwrite}\n")

    results: list[dict] = []

    for voice_id, speaker, label in PRESET_VOICES:
        out_dir = _VOICE_STORAGE_DIR / voice_id
        out_path = out_dir / "sample.wav"

        if not overwrite and out_path.is_file() and _looks_like_audio_file(out_path):
            print(f"[SKIP] {voice_id} ({label}) - already exists")
            results.append({"voice_id": voice_id, "status": "skipped", "path": str(out_path)})
            continue

        print(f"[GEN ] {voice_id} ({label}) speaker={speaker} ...", end="", flush=True)
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            result = generate_tts(
                SAMPLE_TEXT,
                speaker=speaker,
                language="Korean",
                output_path=out_path,
            )
            print(f" done ({result.get('duration_sec', '?')}s)")
            results.append({"voice_id": voice_id, "status": "generated", "path": str(out_path)})
        except Exception as exc:  # noqa: BLE001
            print(f" FAILED: {exc}")
            results.append({"voice_id": voice_id, "status": "failed", "error": str(exc)})

    print("\n=== Result ===")
    ok = 0
    for r in results:
        tag = "OK" if r["status"] in ("generated", "skipped") else "NG"
        print(f"  [{tag}] {r['voice_id']} -> {r['status']}")
        if r["status"] != "failed":
            ok += 1

    print(f"\n{ok}/{len(PRESET_VOICES)} done")
    if ok < len(PRESET_VOICES):
        print("SOME FAILED. Check model install and env vars.")
        sys.exit(1)
    print("SUCCESS. Restart backend to apply sampleAudioUrl.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Preset narrator sample WAV generation")
    parser.add_argument("--overwrite", action="store_true", help="overwrite existing sample.wav")
    args = parser.parse_args()
    generate_all(overwrite=args.overwrite)


if __name__ == "__main__":
    main()

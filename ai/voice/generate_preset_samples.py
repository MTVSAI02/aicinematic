"""기본 나레이션 preset 4개 미리듣기 샘플 WAV 생성 스크립트.

Usage:
    python -m ai.voice.generate_preset_samples            # 파일 없을 때만 생성
    python -m ai.voice.generate_preset_samples --overwrite # 항상 덮어쓰기

Output:
    backend/app/storage/voices/{voiceId}/sample.wav (4 파일)

이 스크립트를 한 번 실행하면 백엔드/프론트가 sampleAudioUrl을 자동으로 잡는다:
    VoiceRepository._stored_preset_sample_url()  ← WAV 헤더 검증 후 URL 반환
    GET /storage/voices/{voiceId}/sample.wav     ← FastAPI 정적 서빙

실행 환경:
    Qwen 패키지(qwen_tts, torch, soundfile)가 있는 venv가 필요하다.
    현재 공용 PC 기준 경로:
        C:\\Users\\WOO\\Documents\\Codex\\comfyui-tts\\.venv\\Scripts\\python.exe

실행 명령 (프로젝트 루트에서):
    & "C:\\Users\\WOO\\Documents\\Codex\\comfyui-tts\\.venv\\Scripts\\python.exe" `
        -m ai.voice.generate_preset_samples
    또는:
    & "C:\\Users\\WOO\\Documents\\Codex\\comfyui-tts\\.venv\\Scripts\\python.exe" `
        -m ai.voice.generate_preset_samples --overwrite
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ── 프로젝트 루트를 sys.path에 추가 ────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

SAMPLE_TEXT = "안녕하세요. 저는 이 목소리로 동화를 들려드릴게요."

# voiceId → (speaker, 한글 이름)
PRESET_VOICES: list[tuple[str, str, str]] = [
    ("voice_preset_narrator_calm_001",    "sohee",  "차분한 나레이션"),
    ("voice_preset_narrator_bright_001",  "serena", "밝은 나레이션"),
    ("voice_preset_narrator_soft_001",    "vivian", "부드러운 나레이션"),
    ("voice_preset_narrator_serious_001", "ryan",   "진지한 나레이션"),
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

    print(f"[preset-samples] Storage: {_VOICE_STORAGE_DIR}")
    print(f"[preset-samples] Sample text: '{SAMPLE_TEXT}'")
    print(f"[preset-samples] Overwrite: {overwrite}\n")

    results: list[dict] = []

    for voice_id, speaker, label in PRESET_VOICES:
        out_dir = _VOICE_STORAGE_DIR / voice_id
        out_path = out_dir / "sample.wav"

        if not overwrite and out_path.is_file() and _looks_like_audio_file(out_path):
            print(f"[SKIP] {voice_id} ({label}) — sample.wav 이미 존재")
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

    print("\n── 결과 요약 ──────────────────────────────────")
    ok = 0
    for r in results:
        icon = "✓" if r["status"] in ("generated", "skipped") else "✗"
        print(f"  {icon} {r['voice_id']} → {r['status']}")
        if r["status"] != "failed":
            ok += 1

    print(f"\n{ok}/{len(PRESET_VOICES)} 완료")
    if ok < len(PRESET_VOICES):
        print("⚠  일부 실패. 모델 설치 및 환경변수를 확인하세요.")
        sys.exit(1)
    print("✓  백엔드 재시작 시 sampleAudioUrl이 자동으로 연결됩니다.")


def main() -> None:
    parser = argparse.ArgumentParser(description="기본 나레이션 preset sample WAV 생성")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="기존 sample.wav가 있어도 덮어쓴다",
    )
    args = parser.parse_args()
    generate_all(overwrite=args.overwrite)


if __name__ == "__main__":
    main()

"""HiDream 캐릭터 생성 **수동 테스트** (파이프라인 아님).

공통 워크플로 러너(ai.comfy_workflow_runner.run_workflow)를 재사용한다.
HTTP/예외/timeout/헤더 정책을 여기서 중복 구현하지 않는다(공통 클라이언트와 갈라지지 않게).
ComfyUI 서버 주소는 COMFYUI_DEFAULT_URL(.env)에서 읽는다 — 하드코딩하지 않는다.

실행:
    uv run --env-file ai/.env python ai/character_ctrl/test_generate.py
"""

import os
import random
import sys
from pathlib import Path

# ai/.env 로드 (python-dotenv 없이 직접 파싱) — COMFYUI_DEFAULT_URL 등
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

# 프로젝트 루트를 path에 추가 (어디서 실행해도 ai 패키지 import 가능)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai.comfy_workflow_runner import run_workflow  # noqa: E402

# 수동 테스트 산출물 저장 위치(확인용). cwd와 무관하도록 절대경로.
_OUTPUT_DIR = (
    Path(__file__).parent.parent.parent / "backend" / "app" / "storage" / "characters"
)


def test_character_generation():
    appearance = (
        "blonde hair, small boy, blue coat, curious eyes, full body, white background"
    )
    seed = random.randint(0, 2**32 - 1)
    print(f"🎨 캐릭터 생성 수동 테스트 (seed={seed})")

    # 공통 러너 사용 → {"images": [bytes, ...]}
    result = run_workflow("character_generate", {"positive_prompt": appearance, "seed": seed})
    images = result["images"]
    if not images:
        print("⚠️  이미지 없음 — ComfyUI UI에서 확인하세요.")
        return

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _OUTPUT_DIR / "test_character.png"
    out_path.write_bytes(images[0])
    print(f"✅ 테스트 성공! 이미지: {out_path}")


if __name__ == "__main__":
    test_character_generation()

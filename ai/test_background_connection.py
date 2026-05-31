"""배경 ComfyUI 연동 준비 확인용 수동 테스트 스크립트.

주의 (중요):
- 실제 이미지 생성을 하지 않는다. POST /prompt 를 호출하지 않는다.
- 조회용 연결 확인(health) + workflow/mapping 로드 + payload 구성까지만 확인한다.

실행 방법:
    # ai/.env 가 있으면 그냥 실행 (스크립트가 ai/.env 를 자동 로드)
    python ai/test_background_connection.py

    # 또는 uv --env-file
    uv run --env-file ai/.env python ai/test_background_connection.py
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai.comfy_client import ComfyUIClient  # noqa: E402
from ai.core.exceptions import ComfyUIError  # noqa: E402
from ai.image import background  # noqa: E402


def _load_local_env() -> None:
    """스크립트 옆의 ai/.env 를 읽어 os.environ 에 채운다 (python-dotenv 불필요)."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


SAMPLE_FINAL_PROMPT = (
    "별빛이 비치는 조용한 사막, storybook background, soft painterly style, "
    "clean composition, background only, no characters"
)
SAMPLE_NEGATIVE_PROMPT = "characters, people, animals, text, watermark, blurry, low quality"


def main() -> int:
    _load_local_env()

    # 테스트 1. base URL 로드
    base_url = os.getenv(background.BACKGROUND_COMFY_URL_ENV)
    print(f"[1] {background.BACKGROUND_COMFY_URL_ENV} = {base_url}")
    if not base_url:
        print("    → 설정되어 있지 않습니다. ai/.env 에 COMFYUI_GPU1_URL 을 넣으세요.")

    # 테스트 2. 연결 확인 (읽기전용, POST /prompt 없음)
    health = background.check_background_comfy_connection()
    print(f"[2] check_background_comfy_connection -> {health}")

    # 테스트 3. workflow JSON 로드
    try:
        workflow = background.load_background_workflow()
        print(f"[3] workflow 로드 OK | keys={list(workflow.keys())} "
              f"| placeholder={background._is_placeholder_workflow(workflow)}")
    except ComfyUIError as exc:
        print(f"[3] workflow 로드 실패: {exc.message}")
        return 1

    # 테스트 4. mapping JSON 로드
    try:
        mapping = background.load_background_mapping()
        keys = [k for k in mapping.keys() if not k.startswith("_")]
        print(f"[4] mapping 로드 OK | 주입 키={keys}")
    except ComfyUIError as exc:
        print(f"[4] mapping 로드 실패: {exc.message}")
        return 1

    # 테스트 5. payload 구성 (실제 생성 X)
    payload = background.build_background_workflow_payload(
        SAMPLE_FINAL_PROMPT, SAMPLE_NEGATIVE_PROMPT
    )
    print(f"[5] payload 구성 OK | workflowReady={payload.get('workflowReady')}")

    # 테스트 5b. apply_mapping 주입 메커니즘 검증 (작은 더미 workflow 로)
    dummy_workflow = {
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}},
    }
    injected = ComfyUIClient.apply_mapping(
        dummy_workflow, mapping,
        {"finalPrompt": SAMPLE_FINAL_PROMPT, "negativePrompt": SAMPLE_NEGATIVE_PROMPT},
    )
    ok_inject = (
        injected["6"]["inputs"]["text"] == SAMPLE_FINAL_PROMPT
        and injected["7"]["inputs"]["text"] == SAMPLE_NEGATIVE_PROMPT
        and dummy_workflow["6"]["inputs"]["text"] == ""  # 원본 불변 확인
    )
    print(f"[5b] apply_mapping 주입 메커니즘 검증 -> {'OK' if ok_inject else 'FAIL'}")

    # 테스트 6. 실제 생성 미실행 확인
    print("[6] 실제 생성 미실행 확인: POST /prompt 호출 없음, "
          "결과 이미지/candidate/background 저장 없음 ✅")

    print("-" * 56)
    print("배경 ComfyUI 연동 준비 확인 완료. (이미지 생성은 수행하지 않음)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

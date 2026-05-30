"""ComfyUI 연결 확인용 수동 테스트 스크립트.

주의 (중요):
- 이 스크립트는 절대 이미지를 생성하지 않는다.
- POST /prompt 를 호출하지 않는다.
- 조회용 API(GET /system_stats, GET /object_info)와 health_check()만 호출한다.

실행 방법 (셋 중 아무거나):
    # 1) ai/.env 만 있으면 그냥 실행 (스크립트가 ai/.env를 자동 로드)
    python ai/test_comfy_connection.py

    # 2) 환경변수를 직접 export
    export COMFYUI_DEFAULT_URL=https://comfy1.mtvs2026.work
    python ai/test_comfy_connection.py

    # 3) uv 의 --env-file 사용
    uv run --env-file ai/.env python ai/test_comfy_connection.py
"""

import os
import sys

# 프로젝트 루트를 import 경로에 추가해 `ai` 패키지를 찾을 수 있게 한다.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai.comfy_client import ComfyUIClient  # noqa: E402
from ai.core.exceptions import ComfyUIConfigError, ComfyUIError  # noqa: E402


def _load_local_env() -> None:
    """스크립트 옆의 ai/.env 파일을 읽어 os.environ에 채운다 (python-dotenv 불필요).

    - 이미 설정된 환경변수는 덮어쓰지 않는다 (export / uv --env-file 가 우선).
    - ai/.env 가 없으면 조용히 넘어간다.
    """
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


def main() -> int:
    _load_local_env()
    try:
        client = ComfyUIClient()
    except ComfyUIConfigError as exc:
        print(f"[CONFIG ERROR] {exc.message}")
        print("→ COMFYUI_DEFAULT_URL 환경변수를 설정한 뒤 다시 실행하세요.")
        return 1

    print(f"baseUrl       = {client.base_url}")
    print(f"timeoutSecond = {client.timeout_seconds}")
    print("-" * 50)

    # 1) health_check (실패해도 예외를 터뜨리지 않고 dict 반환)
    print("[health_check]")
    health = client.health_check()
    print(health)
    print("-" * 50)

    if not health.get("ok"):
        print("연결에 실패했습니다. (서버 미가동/네트워크/URL 확인)")
        return 1

    # 2) 조회용 API 직접 호출 (연결 성공 시에만)
    try:
        stats = client.get_system_stats()
        print("[get_system_stats] keys:", list(stats.keys()))

        object_info = client.get_object_info()
        print("[get_object_info] node count:", len(object_info))
    except ComfyUIError as exc:
        print(f"[ERROR] {exc.message}")
        return 1

    print("-" * 50)
    print("연결 확인 완료. (이미지 생성은 수행하지 않음)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

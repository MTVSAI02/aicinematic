# ⚠️ 임시: AI(ComfyUI) 연결 테스트용 라우터.
# 실제 ComfyUI 연동(JobManager → workflow 실행)이 구현되면 삭제/교체한다.
# 제거 체크리스트: 루트의 TEMP_AI_CONNECTION_TEST.md 참고.
from fastapi import APIRouter

from ai.comfy_client import ComfyUIClient
from ai.core.exceptions import ComfyUIError
from ai.image import background as ai_background

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/comfy-health", summary="ComfyUI 연결 확인 (읽기전용)")
def comfy_health():
    """프론트 → 백엔드 → AI client → ComfyUI(읽기전용) 연결 확인 통로.

    - ai 모듈의 ComfyUIClient.health_check() 만 호출한다.
    - /system_stats, /object_info 조회만 수행하며 이미지 생성(POST /prompt)은 하지 않는다.
    - 설정 누락 등으로 클라이언트 생성 자체가 실패하면 {ok: False, error} 로 응답한다.

    이 엔드포인트는 "프론트 → FastAPI 백엔드 → AI/ComfyUI" 구조를 한 번에 검증하기 위한 것이다.
    """
    try:
        client = ComfyUIClient()
    except ComfyUIError as exc:
        # COMFYUI_DEFAULT_URL 미설정 등 (ComfyUIConfigError 포함)
        return {"ok": False, "error": exc.message}

    return client.health_check()


@router.get("/background-comfy-health", summary="배경 ComfyUI 연결 확인 (읽기전용)")
def background_comfy_health():
    """배경 전용 경로로 ComfyUI 연결을 확인한다.

    - ai/image/background.py 의 check_background_comfy_connection() 만 호출한다.
      (COMFYUI_GPU1_URL 기반, /system_stats·/object_info 조회만)
    - 이미지 생성(POST /prompt)·workflow 실행은 하지 않는다.
    - COMFYUI_GPU1_URL 미설정 등은 {ok: False, error} 로 응답한다.

    "프론트 → 백엔드 → AI 배경 모듈 → ComfyUI(읽기전용)" 경로를 한 번에 검증하기 위한 것이다.
    """
    return ai_background.check_background_comfy_connection()

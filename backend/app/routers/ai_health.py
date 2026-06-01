# ⚠️ 임시: 보이스(TTS) AI 연결 테스트용 라우터.
# 캐릭터/배경은 외부 AI FastAPI 서버 방식으로 전환되어 ComfyUI 직접 health 체크 엔드포인트
# (/comfy-health, /background-comfy-health)는 제거했다.
# TTS/Voice는 아직 실제 연동 테스트 전이라 voice-comfy-health만 남겨둔다.
# 제거 체크리스트: 루트의 TEMP_AI_CONNECTION_TEST.md
from fastapi import APIRouter

from ai.voice import voice as ai_voice

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/voice-comfy-health", summary="보이스(TTS) ComfyUI 연결 확인 (읽기전용)")
def voice_comfy_health():
    """보이스 전용 경로로 ComfyUI 연결을 확인한다.

    - ai/voice/voice.py 의 check_voice_comfy_connection() 만 호출한다.
      (COMFYUI_VOICE_URL 기반, /system_stats·/object_info 조회만)
    - 실제 음성/TTS 생성·보이스 클로닝·workflow 실행(POST /prompt)은 하지 않는다.
    - COMFYUI_VOICE_URL 미설정 등은 {ok: False, error} 로 응답한다.

    "프론트 → 백엔드 → AI 보이스 모듈 → ComfyUI(읽기전용)" 경로를 한 번에 검증하기 위한 것이다.
    """
    return ai_voice.check_voice_comfy_connection()

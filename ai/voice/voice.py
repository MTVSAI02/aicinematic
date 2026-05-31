"""보이스(TTS) ComfyUI 연동 진입점 — 연결 확인 단계.

이번 단계 범위 (중요):
- 보이스 ComfyUI 연결 확인 (읽기전용)

절대 하지 않는 것:
- 실제 음성/TTS 생성, 보이스 클로닝, 샘플 음성 합성
- workflow 실행 (POST /prompt)

원칙: 배경(ai/image/background.py)과 동일하게, AI 는 백엔드가 만든 요청을 받아
실행할 "준비"만 한다. 여기서는 연결 가능 여부만 읽기전용으로 확인한다.
"""

import os

from ..comfy_client import ComfyUIClient
from ..core.exceptions import ComfyUIConfigError

# 보이스/TTS 는 comfy0(COMFYUI_VOICE_URL) 서버를 사용한다. (전용 환경변수)
VOICE_COMFY_URL_ENV = "COMFYUI_VOICE_URL"


def check_voice_comfy_connection() -> dict:
    """보이스 ComfyUI 서버 연결을 확인한다. (읽기전용, POST /prompt 호출 없음)

    성공: {"ok": True, "baseUrl": ..., ...}
    실패/미설정: {"ok": False, "error": ...}
    """
    base_url = os.getenv(VOICE_COMFY_URL_ENV)
    if not base_url or not base_url.strip():
        return {"ok": False, "error": f"{VOICE_COMFY_URL_ENV} is not configured"}

    try:
        client = ComfyUIClient(base_url=base_url)
    except ComfyUIConfigError as exc:
        return {"ok": False, "error": exc.message}

    return client.health_check()

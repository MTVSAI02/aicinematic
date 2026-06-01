import os
from pathlib import Path

# 생성 결과(이미지/오디오/렌더) 저장 루트. backend/app/storage
# ⚠️ 상대경로("backend/app/storage")는 실행 cwd에 따라 달라지므로 쓰지 않는다.
#    __file__ 기준 절대경로로 고정해 어디서 실행하든 같은 위치를 가리키게 한다.
# core/config.py → parent(core) → parent(app) → storage
STORAGE_ROOT = Path(__file__).resolve().parent.parent / "storage"

CHARACTER_STORAGE_DIR = STORAGE_ROOT / "characters"
BACKGROUND_STORAGE_DIR = STORAGE_ROOT / "backgrounds"
BACKGROUND_CANDIDATE_STORAGE_DIR = STORAGE_ROOT / "backgrounds" / "candidates"
AUDIO_STORAGE_DIR = STORAGE_ROOT / "audio"
RENDER_STORAGE_DIR = STORAGE_ROOT / "renders"

# 우리 AI FastAPI 서버 주소 (외부 ComfyUI는 이 AI 서버가 호출한다).
# Backend는 ComfyUI를 직접 호출하지 않고 이 서버의 /generate-character·/generate-background 만 호출한다.
# ⚠️ 실제 주소(IP)는 코드에 하드코딩하지 않고 .env 의 AI_SERVER_URL 로 관리한다.
#   (예시 값은 backend/.env.example 참고)
AI_SERVER_URL = os.getenv("AI_SERVER_URL", "")

# 정적 서빙 URL prefix (main.py 의 app.mount 와 일치)
STORAGE_URL_PREFIX = "/storage"


def storage_url(*parts: str) -> str:
    """정적 서빙 URL을 만든다.

    예: storage_url("characters", "char_mock_001.png")
        → "/storage/characters/char_mock_001.png"
    """
    return "/".join([STORAGE_URL_PREFIX, *parts])

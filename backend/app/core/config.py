import os
from pathlib import Path

# 생성 결과(이미지/오디오/렌더) 저장 루트. backend/app/storage
# ⚠️ 상대경로("backend/app/storage")는 실행 cwd에 따라 달라지므로 쓰지 않는다.
#    __file__ 기준 절대경로로 고정해 어디서 실행하든 같은 위치를 가리키게 한다.
# core/config.py → parent(core) → parent(app) → storage
STORAGE_ROOT = Path(__file__).resolve().parent.parent / "storage"

CHARACTER_STORAGE_DIR = STORAGE_ROOT / "characters"
# 포즈 결과는 원본 캐릭터와 분리 저장(원본 덮어쓰기 금지).
CHARACTER_POSE_STORAGE_DIR = STORAGE_ROOT / "character_poses"
BACKGROUND_STORAGE_DIR = STORAGE_ROOT / "backgrounds"
BACKGROUND_CANDIDATE_STORAGE_DIR = STORAGE_ROOT / "backgrounds" / "candidates"
# 라이브러리에 저장된(선택된) 배경 이미지. 후보 파일에 의존하지 않도록 여기로 복사한다.
BACKGROUND_LIBRARY_STORAGE_DIR = STORAGE_ROOT / "backgrounds" / "library"
AUDIO_STORAGE_DIR = STORAGE_ROOT / "audio"
RENDER_STORAGE_DIR = STORAGE_ROOT / "renders"

# 우리 AI FastAPI 서버 주소 (외부 ComfyUI는 이 AI 서버가 호출한다).
# Backend는 ComfyUI를 직접 호출하지 않고 이 서버의 /generate-character·/generate-background 만 호출한다.
# ⚠️ 실제 주소(IP)는 코드에 하드코딩하지 않고 .env 의 AI_SERVER_URL 로 관리한다.
#   (예시 값은 backend/.env.example 참고)
AI_SERVER_URL = os.getenv("AI_SERVER_URL", "")

# 외부 AI 서버가 Cloudflare 뒤에 있을 때, 기본 httpx UA(python-httpx/...)는 WAF가 403으로 막는다.
# 브라우저형 User-Agent를 보내 차단을 피한다(내부 직결 환경에서도 무해).
AI_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

# 정적 서빙 URL prefix (main.py 의 app.mount 와 일치)
STORAGE_URL_PREFIX = "/storage"


def storage_url(*parts: str) -> str:
    """정적 서빙 URL을 만든다.

    예: storage_url("characters", "char_mock_001.png")
        → "/storage/characters/char_mock_001.png"
    """
    return "/".join([STORAGE_URL_PREFIX, *parts])

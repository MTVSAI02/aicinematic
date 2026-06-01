from pathlib import Path

# 생성 결과(이미지/오디오/렌더) 저장 루트. backend/app/storage
# ⚠️ 상대경로("backend/app/storage")는 실행 cwd에 따라 달라지므로 쓰지 않는다.
#    __file__ 기준 절대경로로 고정해 어디서 실행하든 같은 위치를 가리키게 한다.
# core/config.py → parent(core) → parent(app) → storage
STORAGE_ROOT = Path(__file__).resolve().parent.parent / "storage"

CHARACTER_STORAGE_DIR = STORAGE_ROOT / "characters"
BACKGROUND_STORAGE_DIR = STORAGE_ROOT / "backgrounds"
AUDIO_STORAGE_DIR = STORAGE_ROOT / "audio"
RENDER_STORAGE_DIR = STORAGE_ROOT / "renders"

# 정적 서빙 URL prefix (main.py 의 app.mount 와 일치)
STORAGE_URL_PREFIX = "/storage"


def storage_url(*parts: str) -> str:
    """정적 서빙 URL을 만든다.

    예: storage_url("characters", "char_mock_001.png")
        → "/storage/characters/char_mock_001.png"
    """
    return "/".join([STORAGE_URL_PREFIX, *parts])

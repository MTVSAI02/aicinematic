import os
import shutil
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
# 보이스 클로닝 자산: reference/sample 오디오를 voiceId 별 폴더에 저장. (/storage/voices/{voiceId}/...)
VOICE_STORAGE_DIR = STORAGE_ROOT / "voices"
RENDER_STORAGE_DIR = STORAGE_ROOT / "renders"
# 렌더 중 프레임 PNG 임시 폴더. 완료/실패 후 정리한다. (jobId가 아니라 renderId 기준)
RENDER_TMP_DIR = STORAGE_ROOT / "tmp" / "renders"

# 렌더 출력 규격. 16:9.
RENDER_FPS = 24
RENDER_WIDTH = 1280
RENDER_HEIGHT = 720

# 자막 폰트: 레포의 design/assets/fonts (학교안심 둥근미소). 렌더(Pillow)가 이 OTF로 자막을 그린다.
# core/config.py → parents[3] = 레포 루트.
_REPO_ROOT = Path(__file__).resolve().parents[3]
SUBTITLE_FONT_PATH = (
    _REPO_ROOT / "design/assets/fonts/학교안심 둥근미소/Hakgyoansim Dunggeunmiso OTF R.otf"
)

# 우리 AI FastAPI 서버 주소 (외부 ComfyUI는 이 AI 서버가 호출한다).
# Backend는 ComfyUI를 직접 호출하지 않고 이 서버의 /generate-character·/generate-background 만 호출한다.
# ⚠️ 실제 주소(IP)는 코드에 하드코딩하지 않고 .env 의 AI_SERVER_URL 로 관리한다.
#   (예시 값은 backend/.env.example 참고)
AI_SERVER_URL = os.getenv("AI_SERVER_URL", "")

# 보이스 클로닝 전용 AI 엔드포인트. reference 오디오를 multipart 로 업로드해 클론/샘플을 받는다.
# ⚠️ 실제 주소는 코드에 하드코딩하지 않고 .env 의 AI_VOICE_CLONE_URL 로 관리한다.
AI_VOICE_CLONE_URL = os.getenv("AI_VOICE_CLONE_URL", "")

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


def storage_path(url: str | None) -> Path | None:
    """storage_url 역변환: /storage URL → 실제 디스크 경로.

    예: "/storage/backgrounds/library/bg.png" → STORAGE_ROOT/"backgrounds/library/bg.png"
    /storage 로 시작하지 않는 외부 URL(http…)이나 빈 값은 None(렌더러가 placeholder 처리).
    """
    if not url:
        return None
    prefix = STORAGE_URL_PREFIX + "/"
    if not url.startswith(prefix):
        return None
    return STORAGE_ROOT / url[len(prefix):]


def resolve_ffmpeg_bin() -> str | None:
    """ffmpeg 실행 파일 경로를 우선순위로 찾는다.

    1) FFMPEG_BIN 환경변수(직접 지정) → 2) PATH 의 시스템 ffmpeg → 3) imageio-ffmpeg 번들 바이너리.
    셋 다 없으면 None (렌더러가 FFmpegNotInstalledError 로 명확히 실패).
    """
    env_bin = os.getenv("FFMPEG_BIN")
    if env_bin and Path(env_bin).exists():
        return env_bin
    system_bin = shutil.which("ffmpeg")
    if system_bin:
        return system_bin
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001  (패키지 미설치/바이너리 미동봉 등)
        return None

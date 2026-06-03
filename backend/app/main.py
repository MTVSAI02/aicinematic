import os
import sys
from pathlib import Path

# ── 프로젝트 루트를 sys.path에 추가 ─────────────────────────────────────────
# backend/app/main.py → .parent × 3 = 프로젝트 루트
# 이렇게 해야 'ai' 패키지를 백엔드에서 import 할 수 있다.
_PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ── .env 로드 (backend/.env 우선, 없으면 ai/.env) ───────────────────────────
def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

_load_env(Path(__file__).parent.parent / ".env")        # backend/.env
_load_env(_PROJECT_ROOT / "ai" / ".env")                # ai/.env (fallback)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .core.config import STORAGE_ROOT, STORAGE_URL_PREFIX
from .core.exception_handlers import app_exception_handler
from .core.exceptions import AppException
from .routers import (
    backgrounds,
    characters,
    health,
    jobs,
    render,
    scenes,
    stories,
    timeline,
    tts,
    voices,
)

app = FastAPI(
    title="Mongsil Bookstore API",
    description="Backend API for AI-based moving storybook service",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppException, app_exception_handler)

app.include_router(health.router)
app.include_router(stories.router)
app.include_router(characters.router)
app.include_router(jobs.router)
app.include_router(backgrounds.router)
app.include_router(scenes.router)
app.include_router(timeline.router)
app.include_router(tts.router)
app.include_router(voices.router)
app.include_router(render.router)


@app.get("/")
def root():
    return {"service": "Mongsil Bookstore", "status": "running", "docs": "/docs"}


# ── ⚠️ 임시 개발 시드/스냅샷 (SEED_DEV=1) ───────────────────────────────────────
# ComfyUI/AI 서버 없이 scene-editor를 테스트하기 위한 임시 데이터.
# storage/dev_state.json 으로 백엔드 재시작에도 유지된다(변경마다 저장).
# 실제 생성/영구저장이 안정화되면 이 블록 + core/dev_seed.py + core/dev_persist.py 를 제거한다.
if os.getenv("SEED_DEV") == "1":
    from .core.dev_persist import load_snapshot, save_snapshot
    from .core.dev_seed import seed_dev_data

    if not load_snapshot():   # 스냅샷 있으면 복원, 없으면 기본값 시드 후 스냅샷 생성
        seed_dev_data()
        save_snapshot()

    @app.middleware("http")
    async def _dev_persist_middleware(request, call_next):
        response = await call_next(request)
        # 변경 요청 후 최신 상태를 스냅샷에 저장 (kill로 죽여도 유지)
        if request.method in ("POST", "PATCH", "PUT", "DELETE"):
            save_snapshot()
        return response


@app.on_event("startup")
def _resume_unfinished_tts_jobs():
    from .services.tts_service import tts_service

    tts_service.resume_unfinished_story_tts_jobs()


# 생성된 이미지/오디오 정적 서빙 — 경로는 core/config.py 에서 관리(절대경로)
# 예: /storage/characters/{id}.png
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
app.mount(STORAGE_URL_PREFIX, StaticFiles(directory=str(STORAGE_ROOT)), name="storage")

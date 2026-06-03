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


# ── 보이스 preset 보장 (DB) ───────────────────────────────────────────────────
# voices 는 PostgreSQL 로 이전됨. preset 4개는 Alembic 0002 가 시드하지만, startup 에서도
# idempotent 보장 + sample.wav 존재 여부로 sampleAudioUrl 갱신.
from .repositories.voice_repository import voice_repository as _voice_repo  # noqa: E402

_voice_repo.seed_default_narrator_voices()


@app.on_event("startup")
def _resume_unfinished_tts_jobs():
    from .services.tts_service import tts_service

    tts_service.resume_unfinished_story_tts_jobs()


# 생성된 이미지/오디오 정적 서빙 — 경로는 core/config.py 에서 관리(절대경로)
# 예: /storage/characters/{id}.png
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
app.mount(STORAGE_URL_PREFIX, StaticFiles(directory=str(STORAGE_ROOT)), name="storage")

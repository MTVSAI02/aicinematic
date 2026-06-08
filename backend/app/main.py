# ruff: noqa: E402
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

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

from .core import storage
from .core.config import STORAGE_ROOT
from .core.exception_handlers import app_exception_handler
from .core.exceptions import AppException
from .routers import (
    backgrounds,
    characters,
    health,
    jobs,
    notifications,
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
    # Vercel 배포 프론트(프로덕션·프리뷰 도메인)에서의 호출 허용. *.vercel.app 전부 매칭.
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]

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
app.include_router(notifications.router)


@app.get("/")
def root():
    return {"service": "Mongsil Bookstore", "status": "running", "docs": "/docs"}


@app.on_event("startup")
def _seed_preset_narrator_voices():
    # 기본 나레이션 preset 4종 보장(DB 초기화/팀원 환경에서도 항상 나레이션 선택 가능).
    from .services.preset_voice_seed import seed_preset_narrator_voices

    seed_preset_narrator_voices()


@app.on_event("startup")
def _resume_unfinished_tts_jobs():
    from .services.tts_service import tts_service

    tts_service.resume_unfinished_story_tts_jobs()


@app.on_event("startup")
def _cleanup_unfinished_render_jobs():
    # 서버 재시작으로 죽은 렌더 job(DB에 running/pending 잔존)을 failed 로 정리 → 유령 job 제거.
    from .services.render_service import cleanup_unfinished_render_jobs

    cleanup_unfinished_render_jobs()


# 생성된 이미지/오디오/영상 서빙 — 스토리지 추상화(storage) 경유.
# R2 모드면 R2(get_object)에서, 아니면 로컬 app/storage 에서 읽어 스트리밍한다.
# (정적 StaticFiles 마운트 대신 프록시 라우트 — R2 비공개 버킷도 백엔드 통해서만 접근)
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)  # 로컬 모드 저장 대비


@app.get("/storage/{path:path}", include_in_schema=False)
def serve_storage(path: str):
    data = storage.read_bytes(path)
    if data is None:
        raise HTTPException(status_code=404, detail="File not found")
    return Response(content=data, media_type=storage.content_type_for(path))

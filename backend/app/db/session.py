"""DB 엔진/세션 관리.

- engine: DATABASE_URL(psycopg3) 기반, pool_pre_ping.
- SessionLocal: expire_on_commit=False (repo가 commit 후에도 객체 값을 dict 로 변환할 수 있게).
- get_db: FastAPI 요청 스코프 의존성.
- session_scope: 백그라운드 job(요청 밖) 전용 — with 블록 종료 시 commit/rollback.
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # main.py 가 backend/.env 를 먼저 로드한다. 그래도 없으면 명확히 알린다.
    raise RuntimeError("DATABASE_URL 환경변수가 없습니다 (backend/.env 확인).")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def get_db() -> Iterator[Session]:
    """FastAPI 요청 스코프 세션. 라우터에서 Depends(get_db) 로 사용."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """백그라운드 job/스크립트용 세션. 정상 종료 시 commit, 예외 시 rollback."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

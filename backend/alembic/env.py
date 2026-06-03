"""Alembic 환경 설정.

- backend/.env 의 DATABASE_URL 을 읽어 접속 (alembic.ini 의 sqlalchemy.url 대신).
- target_metadata = app.db.models 의 Base.metadata (autogenerate 기준).
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# --- backend 디렉터리를 import 경로에 추가 (env.py 는 backend/alembic/ 안) ---
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


def _load_env(path: Path) -> None:
    """backend/.env 의 KEY=VALUE 를 os.environ 에 주입(이미 있으면 유지). 주석(#)·빈 줄 무시."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


_load_env(_BACKEND_DIR / ".env")

from app.db.base import Base  # noqa: E402
import app.db.models  # noqa: E402,F401  (모델 등록 → metadata 채움)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

_DB_URL = os.environ.get("DATABASE_URL")
if _DB_URL:
    config.set_main_option("sqlalchemy.url", _DB_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

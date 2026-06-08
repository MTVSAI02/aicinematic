"""scene duration 최대값 30초 -> 180초 (씬당 길이 상한 확대)

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-09

scenes.duration CHECK 제약(ck_scenes_scene_duration_range)을 1~30 → 1~180 으로 교체.
제약명을 명시한 raw SQL 로 drop/add (naming convention 의존 없이 동일 이름 유지).
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NAME = "ck_scenes_scene_duration_range"


def upgrade() -> None:
    op.execute(f"ALTER TABLE scenes DROP CONSTRAINT {_NAME}")
    op.execute(
        f"ALTER TABLE scenes ADD CONSTRAINT {_NAME} "
        "CHECK (duration >= 1.0 and duration <= 180.0)"
    )


def downgrade() -> None:
    op.execute(f"ALTER TABLE scenes DROP CONSTRAINT {_NAME}")
    op.execute(
        f"ALTER TABLE scenes ADD CONSTRAINT {_NAME} "
        "CHECK (duration >= 1.0 and duration <= 30.0)"
    )

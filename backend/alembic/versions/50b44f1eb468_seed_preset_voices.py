"""seed preset voices — ⛔ 폐지(no-op)

원래는 기본 나레이션 preset 보이스 4개를 시드했으나, **preset 자동 시드 정책이 폐지**되어
이 마이그레이션은 더 이상 아무 데이터도 넣지 않는다(no-op). 보이스는 화면/클론 플로우에서 생성한다.
리비전 체인 유지를 위해 파일/리비전 ID 는 그대로 둔다.

Revision ID: 50b44f1eb468
Revises: ecfe127bd397
Create Date: 2026-06-04 01:33:54.652508
"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = '50b44f1eb468'
down_revision: Union[str, Sequence[str], None] = 'ecfe127bd397'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # preset 보이스 자동 시드 폐지 — no-op.
    pass


def downgrade() -> None:
    # no-op.
    pass

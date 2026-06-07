"""scenes.subtitle_background 컬럼 추가

자막 배경 박스 옵션(씬 단위). 값: none/black/white (null=none).
글자색(scene_text_color)과 동일한 씬 단위 자막 설정.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
"""
from alembic import op
import sqlalchemy as sa

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scenes", sa.Column("subtitle_background", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("scenes", "subtitle_background")

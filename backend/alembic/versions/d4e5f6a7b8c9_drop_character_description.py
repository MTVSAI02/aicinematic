"""characters.description 컬럼 제거

/character 화면에서 "외형 설명"(description) 입력을 폐지함에 따라 컬럼까지 완전 삭제.
(AI 생성에는 appearance_prompt 만 사용하므로 영향 없음. voices.description 과는 무관.)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
"""
from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("characters", "description")


def downgrade() -> None:
    op.add_column("characters", sa.Column("description", sa.Text(), nullable=True))

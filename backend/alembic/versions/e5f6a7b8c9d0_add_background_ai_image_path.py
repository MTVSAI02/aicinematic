"""backgrounds.ai_image_path 컬럼 추가

배경 생성 시 AI 서버 원본 경로(/generate-background 응답의 image_path)를 보관(확장 대비, 내부 전용).
캐릭터의 ai_image_path 와 동일한 성격(우리 storage 이미지 image_url 과 별개).

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
"""
from alembic import op
import sqlalchemy as sa

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("backgrounds", sa.Column("ai_image_path", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("backgrounds", "ai_image_path")

"""scene_characters.scene_appearance_prompt 추가 + tts_audios (scene_id,item_index) UNIQUE 제거

- scene_appearance_prompt: 씬별 캐릭터 연출 프롬프트(서비스가 저장하던 값) 보존용 컬럼.
- uq_ttsaudio_scene_item 제거: 대상별 TTS 재생성이 "기존 audio 유지 + 새 audio 생성 후 교체"
  (success-after-replace) 패턴이라 같은 (scene_id,item_index) 의 old/new 가 잠시 공존한다.
  PK(audioId)로 충분히 식별되므로 이 UNIQUE 는 제거한다.

Revision ID: a1b2c3d4e5f6
Revises: 50b44f1eb468
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "50b44f1eb468"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scene_characters",
        sa.Column("scene_appearance_prompt", sa.Text(), nullable=True),
    )
    op.drop_constraint("uq_ttsaudio_scene_item", "tts_audios", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_ttsaudio_scene_item", "tts_audios", ["scene_id", "item_index"]
    )
    op.drop_column("scene_characters", "scene_appearance_prompt")

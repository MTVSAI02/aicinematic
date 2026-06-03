"""seed preset voices

Revision ID: 50b44f1eb468
Revises: ecfe127bd397
Create Date: 2026-06-04 01:33:54.652508

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert


# revision identifiers, used by Alembic.
revision: str = '50b44f1eb468'
down_revision: Union[str, Sequence[str], None] = 'ecfe127bd397'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_PRESETS = [
    ("voice_preset_narrator_calm_001", "차분한 나레이션", "잔잔하고 따뜻하게 동화를 읽어주는 목소리",
     "calm, warm, gentle narrator voice for fairy tale storytelling"),
    ("voice_preset_narrator_bright_001", "밝은 나레이션", "밝고 친근하게 이야기를 읽어주는 목소리",
     "bright, friendly, cheerful narrator voice for children story"),
    ("voice_preset_narrator_soft_001", "부드러운 나레이션", "포근하고 부드러운 분위기의 동화 구연 목소리",
     "soft, cozy, gentle storytelling voice"),
    ("voice_preset_narrator_serious_001", "진지한 나레이션", "안정감 있고 차분하게 장면을 설명하는 목소리",
     "serious, calm, stable narrator voice"),
]


def upgrade() -> None:
    """기본 나레이션 preset 4개 시드 (시스템 고정 ID, is_preset=true, ready). 재실행 안전(ON CONFLICT)."""
    voices = sa.table(
        "voices",
        sa.column("id", sa.Text), sa.column("name", sa.Text), sa.column("description", sa.Text),
        sa.column("voice_prompt", sa.Text), sa.column("voice_type", sa.Text),
        sa.column("is_preset", sa.Boolean), sa.column("status", sa.Text),
        sa.column("sample_audio_url", sa.Text),
    )
    for vid, name, desc, prompt in _PRESETS:
        stmt = pg_insert(voices).values(
            id=vid, name=name, description=desc, voice_prompt=prompt,
            voice_type="narrator", is_preset=True, status="ready",
            sample_audio_url=f"/storage/voices/{vid}/sample.wav",
        ).on_conflict_do_nothing(index_elements=["id"])  # 이미 있으면 무시(idempotent)
        op.execute(stmt)


def downgrade() -> None:
    op.execute(
        "DELETE FROM voices WHERE id IN ("
        "'voice_preset_narrator_calm_001','voice_preset_narrator_bright_001',"
        "'voice_preset_narrator_soft_001','voice_preset_narrator_serious_001')"
    )

"""DB 모델 (PostgreSQL).

ID 정책: 모든 PK = prefix+ULID 문자열(text). 숫자 PK/중복 식별자 컬럼 없음.
legacy_id: mock 마이그레이션 추적용(운영 로직 미사용).
파일은 storage 에 저장하고 *_url/*_path 컬럼엔 경로만 저장.
글자색/배치/cue 같은 중첩 덩어리는 JSONB. updated_at 은 DB 트리거로 갱신(0001 참조).
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

# 공통 타임스탬프 컬럼 (updated_at 은 DB 트리거가 갱신)
_TS = DateTime(timezone=True)


class Voice(Base):
    __tablename__ = "voices"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    legacy_id: Mapped[str | None] = mapped_column(Text, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    voice_prompt: Mapped[str | None] = mapped_column(Text)
    voice_type: Mapped[str] = mapped_column(Text, nullable=False, server_default="character")
    is_preset: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"), index=True)
    speaker_label: Mapped[str | None] = mapped_column(Text)
    # "어느 캐릭터용으로 만들었나" 메타 — 순환 FK 회피 위해 plain text(FK 아님)
    character_id: Mapped[str | None] = mapped_column(Text)
    reference_audio_url: Mapped[str | None] = mapped_column(Text)
    reference_text: Mapped[str | None] = mapped_column(Text)
    sample_audio_url: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending", index=True)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())
    __table_args__ = (
        CheckConstraint("voice_type in ('narrator','character')", name="voice_type_valid"),
        CheckConstraint(
            "status in ('pending','processing','ready','failed')", name="voice_status_valid"
        ),
    )


class Background(Base):
    __tablename__ = "backgrounds"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    legacy_id: Mapped[str | None] = mapped_column(Text, index=True)
    name: Mapped[str | None] = mapped_column(Text)
    prompt: Mapped[str | None] = mapped_column(Text)
    final_prompt: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)  # storage path
    created_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())


class Character(Base):
    __tablename__ = "characters"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    legacy_id: Mapped[str | None] = mapped_column(Text, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    appearance_prompt: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)  # storage path
    ai_image_path: Mapped[str | None] = mapped_column(Text)  # 포즈 생성용 원본
    voice_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("voices.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())


class CharacterPose(Base):
    __tablename__ = "character_poses"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    legacy_id: Mapped[str | None] = mapped_column(Text, index=True)
    character_id: Mapped[str] = mapped_column(
        Text, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    prompt: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())


class Story(Base):
    __tablename__ = "stories"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    legacy_id: Mapped[str | None] = mapped_column(Text, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    narrator_voice_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("voices.id", ondelete="SET NULL")
    )
    # 대상별 잠금 {targetId:{lockStatus,ttsStatus,gen}}
    voice_locks: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())


class Scene(Base):
    __tablename__ = "scenes"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    legacy_id: Mapped[str | None] = mapped_column(Text, index=True)
    story_id: Mapped[str] = mapped_column(
        Text, ForeignKey("stories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("3.0"))
    background_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("backgrounds.id", ondelete="SET NULL")
    )
    scene_text_color: Mapped[str | None] = mapped_column(Text)  # null=자동(렌더 기본 검정)
    items: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    cue_timings: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    subtitle_settings: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())
    __table_args__ = (
        UniqueConstraint("story_id", "order_index", name="uq_scene_story_order"),
        CheckConstraint("duration >= 1.0 and duration <= 30.0", name="scene_duration_range"),
    )


class SceneCharacter(Base):
    __tablename__ = "scene_characters"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    scene_id: Mapped[str] = mapped_column(
        Text, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    character_id: Mapped[str] = mapped_column(
        Text, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pose_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("character_poses.id", ondelete="SET NULL")
    )
    scene_appearance_prompt: Mapped[str | None] = mapped_column(Text)  # 씬별 캐릭터 연출(저장만)
    layout: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())
    __table_args__ = (
        UniqueConstraint("scene_id", "character_id", name="uq_scene_character"),
    )


class TtsAudio(Base):
    __tablename__ = "tts_audios"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    legacy_id: Mapped[str | None] = mapped_column(Text, index=True)
    scene_id: Mapped[str] = mapped_column(
        Text, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 보조(조회 최적화) — scene 으로도 도달 가능하지만 story 단위 조회가 잦음
    story_id: Mapped[str] = mapped_column(
        Text, ForeignKey("stories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_index: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str | None] = mapped_column(Text)  # narration | dialogue
    speaker: Mapped[str | None] = mapped_column(Text)
    text: Mapped[str | None] = mapped_column(Text)
    emotion: Mapped[str | None] = mapped_column(Text)
    emotion_label: Mapped[str | None] = mapped_column(Text)
    voice_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("voices.id", ondelete="SET NULL"), index=True
    )
    audio_url: Mapped[str | None] = mapped_column(Text)  # storage path
    duration_sec: Mapped[float | None] = mapped_column(Float)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())
    # (scene_id,item_index) UNIQUE 없음 — TTS 재생성 시 old/new 가 잠시 공존(success-after-replace).


class RenderResult(Base):
    __tablename__ = "render_results"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    legacy_id: Mapped[str | None] = mapped_column(Text, index=True)
    story_id: Mapped[str] = mapped_column(
        Text, ForeignKey("stories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    video_url: Mapped[str] = mapped_column(Text, nullable=False)  # storage path
    duration: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="completed")
    created_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())
    __table_args__ = (
        CheckConstraint(
            "status in ('generating','completed','failed')", name="render_status_valid"
        ),
    )


class Job(Base):
    """비동기 작업(캐릭터/배경/TTS/클론/렌더) 상태. PostgreSQL 영속 → 재시작 후 복구 가능.

    id = prefix+ULID (job_…) → 카운터 충돌 없음. result/payload 는 JSONB.
    story_id 는 plain text(FK 아님) — 작업이 스토리보다 오래 남거나 임의 참조 가능.
    """
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    story_id: Mapped[str | None] = mapped_column(Text, index=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending", index=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    result: Mapped[dict | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())
    __table_args__ = (
        CheckConstraint(
            "status in ('pending','running','completed','failed')", name="job_status_valid"
        ),
    )


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    legacy_id: Mapped[str | None] = mapped_column(Text, index=True)
    email: Mapped[str | None] = mapped_column(Text, unique=True)
    display_name: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())


class Notification(Base):
    """job 완료/실패 알림. job 1건 → 알림 1건(UNIQUE(related_job_id,type) 로 중복 방지).

    user 기능 전이라 user_id 는 nullable(전역 알림). id = prefix+ULID(notif_).
    related_* 는 plain text(FK 아님) — 알림은 운영 메타라 대상 삭제와 독립.
    """
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str | None] = mapped_column(Text, index=True)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    related_job_id: Mapped[str | None] = mapped_column(Text, index=True)
    related_story_id: Mapped[str | None] = mapped_column(Text)
    related_scene_id: Mapped[str | None] = mapped_column(Text)
    related_target_id: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"), index=True)
    created_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())
    read_at: Mapped[datetime | None] = mapped_column(_TS)
    __table_args__ = (
        UniqueConstraint("related_job_id", "type", name="uq_notification_job_type"),
    )

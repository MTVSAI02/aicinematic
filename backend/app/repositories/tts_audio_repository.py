"""TTS audio 결과 repository (PostgreSQL).

기존 in-memory 와 같은 메서드/반환(dict, camelCase)을 유지한다.

설계 포인트
- 저장은 **lean**(audioUrl/durationSec/error/emotion/type/speaker/text + FK)만. AI 합성 payload 에 필요한
  voicePrompt/characterPrompt/reference_* 등 rich 필드는 저장하지 않고, create_many 가 입력 dict 를
  그대로 echo + audioId 만 붙여 반환한다(서비스가 그 반환값으로 AI 호출 → DB엔 lean 영속).
- 서비스는 API 노출 sceneId(scene_001)로 호출 → 내부에서 (story_id,order)로 scenes.id(ULID) 해소.
- (scene_id,item_index) UNIQUE 없음 → 대상별 재생성 시 old/new 공존 허용(success-after-replace).
"""

from __future__ import annotations

import re

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..core.ids import new_id
from ..db.models import Scene, TtsAudio
from ..db.session import SessionLocal

_ORDER_RE = re.compile(r"(\d+)")


def _parse_order(local_scene_id: str) -> int | None:
    m = _ORDER_RE.search(local_scene_id or "")
    return int(m.group(1)) if m else None


def _emotion_str(value) -> str | None:
    """emotion 은 보통 문자열 키. 혹시 (key,label) 튜플/리스트로 오면 key 만 취한다."""
    if isinstance(value, (list, tuple)):
        return value[0] if value else None
    return value


class TTSAudioRepository:
    @staticmethod
    def _scene_pk(db: Session, story_id: str, local_scene_id: str) -> str | None:
        order = _parse_order(local_scene_id)
        if order is None:
            return None
        return db.execute(
            select(Scene.id).where(Scene.story_id == story_id, Scene.order_index == order)
        ).scalar_one_or_none()

    @staticmethod
    def _local_scene_id(db: Session, scene_pk: str, cache: dict) -> str | None:
        if scene_pk in cache:
            return cache[scene_pk]
        order = db.execute(select(Scene.order_index).where(Scene.id == scene_pk)).scalar_one_or_none()
        local = f"scene_{order:03d}" if order is not None else None
        cache[scene_pk] = local
        return local

    def _to_dict(self, db: Session, a: TtsAudio, cache: dict, local_scene_id: str | None = None) -> dict:
        return {
            "audioId": a.id,
            "storyId": a.story_id,
            "sceneId": local_scene_id or self._local_scene_id(db, a.scene_id, cache),
            "itemIndex": a.item_index,
            "type": a.type,
            "speaker": a.speaker,
            "text": a.text,
            "emotion": a.emotion,
            "emotionLabel": a.emotion_label,
            # voiceType 은 저장 안 함(파생): narration→narrator, 그 외→character. (응답 스키마 필수)
            "voiceType": "narrator" if a.type == "narration" else "character",
            "voiceId": a.voice_id,
            "audioUrl": a.audio_url,
            "durationSec": a.duration_sec,
            "error": a.error,
        }

    # ── 생성 ─────────────────────────────────────────────────
    def create_many(self, audios: list[dict]) -> list[dict]:
        """audio 목록 저장(audioId 발급). 반환은 입력 dict(rich) + audioId — AI payload 용."""
        saved = []
        with SessionLocal() as db:
            for a in audios:
                scene_pk = self._scene_pk(db, a.get("storyId"), a.get("sceneId"))
                if scene_pk is None:
                    continue  # 해소 불가한 씬(방어) — 건너뜀
                audio_id = new_id("tts_audio")
                db.add(TtsAudio(
                    id=audio_id,
                    scene_id=scene_pk,
                    story_id=a.get("storyId"),
                    item_index=a.get("itemIndex"),
                    type=a.get("type"),
                    speaker=a.get("speaker"),
                    text=a.get("text"),
                    emotion=_emotion_str(a.get("emotion")),
                    emotion_label=a.get("emotionLabel"),
                    voice_id=a.get("voiceId"),
                    audio_url=a.get("audioUrl"),
                    duration_sec=a.get("durationSec"),
                    error=a.get("error"),
                ))
                saved.append({**a, "audioId": audio_id})
            db.commit()
        return saved

    def create_one_fixed(self, audio_id: str, a: dict, scene_pk: str) -> None:
        """마이그레이션 전용: 기존 audioId + 해소된 scene_pk 로 1건 삽입(idempotent 은 호출측 책임)."""
        with SessionLocal() as db:
            db.add(TtsAudio(
                id=audio_id,
                legacy_id=audio_id,
                scene_id=scene_pk,
                story_id=a.get("storyId"),
                item_index=a.get("itemIndex"),
                type=a.get("type"),
                speaker=a.get("speaker"),
                text=a.get("text"),
                emotion=_emotion_str(a.get("emotion")),
                emotion_label=a.get("emotionLabel"),
                voice_id=a.get("voiceId"),
                audio_url=a.get("audioUrl"),
                duration_sec=a.get("durationSec"),
                error=a.get("error"),
            ))
            db.commit()

    def upsert_target(self, audio: dict, audio_id: str | None = None) -> dict:
        """item 하나를 저장/갱신한다(story TTS 재개 흐름용). audio_id 주면 그 row 갱신, 없으면 신규.

        반환은 입력 dict(rich) + audioId — create_many 와 동일하게 AI payload 로 재사용 가능.
        """
        with SessionLocal() as db:
            scene_pk = self._scene_pk(db, audio.get("storyId"), audio.get("sceneId"))
            if scene_pk is None:
                return {**audio, "audioId": audio_id}  # 해소 불가(방어) — passthrough
            row = db.get(TtsAudio, audio_id) if audio_id else None
            if row is None:
                audio_id = audio_id or new_id("tts_audio")
                row = TtsAudio(id=audio_id)
                db.add(row)
            row.scene_id = scene_pk
            row.story_id = audio.get("storyId")
            row.item_index = audio.get("itemIndex")
            row.type = audio.get("type")
            row.speaker = audio.get("speaker")
            row.text = audio.get("text")
            row.emotion = _emotion_str(audio.get("emotion"))
            row.emotion_label = audio.get("emotionLabel")
            row.voice_id = audio.get("voiceId")
            row.audio_url = audio.get("audioUrl")
            row.duration_sec = audio.get("durationSec")
            row.error = audio.get("error")
            db.commit()
            return {**audio, "audioId": row.id}

    # ── 조회 ─────────────────────────────────────────────────
    def list_by_scene(self, story_id: str, scene_id: str) -> list[dict]:
        with SessionLocal() as db:
            scene_pk = self._scene_pk(db, story_id, scene_id)
            if scene_pk is None:
                return []
            rows = db.execute(
                select(TtsAudio).where(TtsAudio.scene_id == scene_pk).order_by(TtsAudio.item_index)
            ).scalars().all()
            # item_index 당 1건으로 정리(재생성 old/new 공존 시 audioUrl 있는 것 우선) — develop 흐름과 일치.
            by_item: dict = {}
            for a in rows:
                cur = by_item.get(a.item_index)
                if cur is None or (a.audio_url and not cur.audio_url):
                    by_item[a.item_index] = a
            return [self._to_dict(db, by_item[k], {}, local_scene_id=scene_id) for k in sorted(by_item)]

    def list_by_story(self, story_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.execute(
                select(TtsAudio).where(TtsAudio.story_id == story_id)
            ).scalars().all()
            cache: dict = {}
            return [self._to_dict(db, a, cache) for a in rows]

    def get(self, audio_id: str) -> dict | None:
        with SessionLocal() as db:
            a = db.get(TtsAudio, audio_id)
            return self._to_dict(db, a, {}) if a else None

    # ── 갱신(AI 결과 반영) ────────────────────────────────────
    def apply_ai_result(self, audios: list[dict]) -> list[dict]:
        """AI/TTS 응답을 audioId 기준으로 audioUrl/durationSec/error 에 반영한다."""
        updated = []
        with SessionLocal() as db:
            cache: dict = {}
            for audio in audios:
                audio_id = audio.get("audioId")
                if not audio_id:
                    continue
                a = db.get(TtsAudio, audio_id)
                if a is None:
                    continue
                a.audio_url = audio.get("audioUrl")
                a.duration_sec = audio.get("durationSec")
                a.error = audio.get("error")
                updated.append(self._to_dict(db, a, cache))
            db.commit()
        return updated

    # ── 삭제 ─────────────────────────────────────────────────
    def delete(self, audio_id: str) -> bool:
        with SessionLocal() as db:
            a = db.get(TtsAudio, audio_id)
            if a is None:
                return False
            db.delete(a)
            db.commit()
            return True

    def delete_by_scene(self, story_id: str, scene_id: str) -> int:
        """특정 story+scene 의 기존 audio 전부 삭제(재생성 교체용). 삭제 개수 반환."""
        with SessionLocal() as db:
            scene_pk = self._scene_pk(db, story_id, scene_id)
            if scene_pk is None:
                return 0
            res = db.execute(delete(TtsAudio).where(TtsAudio.scene_id == scene_pk))
            db.commit()
            return res.rowcount or 0


tts_audio_repository = TTSAudioRepository()

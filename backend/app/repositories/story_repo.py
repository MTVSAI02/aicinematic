"""스토리/씬/씬-캐릭터 repository (PostgreSQL).

기존 in-memory 와 같은 메서드/반환(임베디드 dict, camelCase)을 유지한다.

설계 포인트
- scenes.id PK = prefix+ULID(전역 유일). **API 노출 sceneId = f"scene_{order:03d}"** 로 재구성
  → 프론트 계약(scene_001 …) 그대로. (order_index 는 파싱 후 변경하지 않으므로 sceneId↔order 안정)
- 씬은 파싱 때 한 번 생성되고 이후 추가/삭제되지 않는다(필드/연결만 수정).
- 서비스는 story dict 를 get() 으로 받아 **그 자리에서 수정한 뒤** save_story() 로 통째 upsert 한다
  (in-memory dict 직접변형 → DB 영속화로 전환). scene_characters 는 (scene,character) 기준 upsert.
- voiceLocks 는 stories.voice_locks(JSONB). lastRender 는 render_results 최신 1건에서 파생.
- 배경/캐릭터 삭제 시 scene 참조 정리는 FK(SET NULL / CASCADE)가 담당 → 여기서 수동 정리 안 함.
"""

from __future__ import annotations

import re

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..core.ids import new_id
from ..db.models import RenderResult, Scene, SceneCharacter, Story, TtsAudio
from ..db.session import SessionLocal

_SCENE_ID_RE = re.compile(r"(\d+)")


def _local_scene_id(order_index: int) -> str:
    return f"scene_{order_index:03d}"


def _parse_order(local_scene_id: str) -> int | None:
    m = _SCENE_ID_RE.search(local_scene_id or "")
    return int(m.group(1)) if m else None


def _scene_char_to_dict(sc: SceneCharacter) -> dict:
    return {
        "characterId": sc.character_id,
        "sceneAppearancePrompt": sc.scene_appearance_prompt,
        "poseId": sc.pose_id,
        "layout": sc.layout or None,
    }


def _scene_to_dict(scene: Scene, scene_chars: list[SceneCharacter]) -> dict:
    return {
        "sceneId": _local_scene_id(scene.order_index),
        "order": scene.order_index,
        "duration": scene.duration,
        "backgroundId": scene.background_id,
        "items": scene.items or [],
        "subtitleSettings": scene.subtitle_settings or {},
        "cueTimings": scene.cue_timings or [],
        "sceneTextColor": scene.scene_text_color,
        "subtitleBackground": scene.subtitle_background,
        "characters": [_scene_char_to_dict(c) for c in scene_chars],
    }


def _latest_render_dict(db: Session, story_id: str) -> dict | None:
    r = db.execute(
        select(RenderResult)
        .where(RenderResult.story_id == story_id)
        .order_by(RenderResult.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if r is None:
        return None
    return {
        "renderId": r.id,
        "videoUrl": r.video_url,
        "duration": r.duration,
        "createdAt": r.created_at.isoformat() if r.created_at else None,
    }


def _story_to_dict(db: Session, story: Story) -> dict:
    scenes = db.execute(
        select(Scene).where(Scene.story_id == story.id).order_by(Scene.order_index)
    ).scalars().all()
    chars = db.execute(
        select(SceneCharacter)
        .join(Scene, SceneCharacter.scene_id == Scene.id)
        .where(Scene.story_id == story.id)
        .order_by(SceneCharacter.created_at)
    ).scalars().all()
    by_scene: dict[str, list] = {}
    for c in chars:
        by_scene.setdefault(c.scene_id, []).append(c)
    return {
        "storyId": story.id,
        "title": story.title,
        "narratorVoiceId": story.narrator_voice_id,
        "voiceLocks": story.voice_locks or {},
        "lastRender": _latest_render_dict(db, story.id),
        "scenes": [_scene_to_dict(s, by_scene.get(s.id, [])) for s in scenes],
    }


class StoryRepository:
    # ── 생성(파싱 저장) ───────────────────────────────────────
    def save(self, story_data: dict) -> dict:
        """파서 결과(title + scenes)를 새 스토리로 저장. 마이그레이션 시 legacyId/기존 id 수용."""
        story_id = story_data.get("storyId") or new_id("story")
        with SessionLocal() as db:
            db.add(Story(
                id=story_id,
                title=story_data.get("title"),
                narrator_voice_id=story_data.get("narratorVoiceId"),
                voice_locks=story_data.get("voiceLocks") or {},
                legacy_id=story_data.get("legacyId"),
            ))
            db.flush()  # 스토리 row 를 먼저 확정해야 scenes FK(story_id) 가 통과한다
            for sc in story_data.get("scenes") or []:
                self._insert_scene(db, story_id, sc)
            db.commit()
            return self._get(db, story_id)

    @staticmethod
    def _insert_scene(db: Session, story_id: str, sc: dict) -> str:
        scene_id = new_id("scene")
        db.add(Scene(
            id=scene_id,
            story_id=story_id,
            order_index=int(sc.get("order")),
            duration=float(sc.get("duration") or 3.0),
            background_id=sc.get("backgroundId"),
            scene_text_color=sc.get("sceneTextColor"),
            subtitle_background=sc.get("subtitleBackground"),
            items=sc.get("items") or [],
            cue_timings=sc.get("cueTimings") or [],
            subtitle_settings=sc.get("subtitleSettings") or {},
        ))
        db.flush()  # scene row 확정 후 scene_characters FK(scene_id) 통과
        for ch in sc.get("characters") or []:
            db.add(SceneCharacter(
                id=new_id("scene_character"),
                scene_id=scene_id,
                character_id=ch.get("characterId"),
                scene_appearance_prompt=ch.get("sceneAppearancePrompt"),
                pose_id=ch.get("poseId"),
                layout=ch.get("layout") or {},
            ))
        return scene_id

    # ── 조회 ─────────────────────────────────────────────────
    @staticmethod
    def _get(db: Session, story_id: str) -> dict | None:
        story = db.get(Story, story_id)
        return _story_to_dict(db, story) if story else None

    def get(self, story_id: str) -> dict | None:
        with SessionLocal() as db:
            return self._get(db, story_id)

    def list(self) -> list[dict]:
        with SessionLocal() as db:
            stories = db.execute(select(Story).order_by(Story.created_at)).scalars().all()
            return [_story_to_dict(db, s) for s in stories]

    def delete(self, story_id: str) -> dict | None:
        """스토리 삭제. 없으면 None.

        FK CASCADE 로 scenes/scene_characters/tts_audios/render_results 가 함께 삭제된다.
        삭제 전, 정리해야 할 storage 파일 URL(TTS 오디오 + 렌더 mp4)을 모아 반환한다.
        (characters/backgrounds 는 공용 라이브러리라 건드리지 않는다 — story FK 없음.)
        """
        with SessionLocal() as db:
            story = db.get(Story, story_id)
            if story is None:
                return None
            audio_urls = db.execute(
                select(TtsAudio.audio_url).where(
                    TtsAudio.story_id == story_id, TtsAudio.audio_url.is_not(None)
                )
            ).scalars().all()
            video_urls = db.execute(
                select(RenderResult.video_url).where(RenderResult.story_id == story_id)
            ).scalars().all()
            db.delete(story)  # CASCADE: scenes/scene_characters/tts_audios/render_results
            db.commit()
            return {
                "storyId": story_id,
                "audioUrls": list(audio_urls),
                "videoUrls": list(video_urls),
            }

    def resolve_scene_pk(self, story_id: str, local_scene_id: str) -> str | None:
        """API 노출 sceneId(scene_001) → 실제 scenes.id(ULID). 없으면 None. (tts repo 등에서 사용)"""
        order = _parse_order(local_scene_id)
        if order is None:
            return None
        with SessionLocal() as db:
            return db.execute(
                select(Scene.id).where(Scene.story_id == story_id, Scene.order_index == order)
            ).scalar_one_or_none()

    # ── 통째 upsert (서비스가 dict 수정 후 호출) ───────────────
    def save_story(self, story: dict) -> dict:
        """story dict(scenes/characters 포함)를 DB 에 반영한다.

        스토리 메타 + 각 scene 의 가변 필드 + scene_characters 를 (scene,character) 기준 upsert 한다.
        씬 추가/삭제는 일어나지 않는다(있는 씬만 갱신). 없는 씬 id 는 무시.
        """
        story_id = story.get("storyId")
        with SessionLocal() as db:
            row = db.get(Story, story_id)
            if row is None:
                return None
            row.title = story.get("title", row.title)
            row.narrator_voice_id = story.get("narratorVoiceId")
            row.voice_locks = story.get("voiceLocks") or {}

            scene_rows = db.execute(
                select(Scene).where(Scene.story_id == story_id)
            ).scalars().all()
            by_order = {s.order_index: s for s in scene_rows}
            for sc in story.get("scenes") or []:
                order = sc.get("order")
                if order is None:
                    order = _parse_order(sc.get("sceneId"))
                scene = by_order.get(order)
                if scene is None:
                    continue
                if sc.get("duration") is not None:
                    scene.duration = float(sc["duration"])
                if "backgroundId" in sc:
                    scene.background_id = sc["backgroundId"]
                if "sceneTextColor" in sc:
                    scene.scene_text_color = sc["sceneTextColor"]
                if "subtitleBackground" in sc:
                    scene.subtitle_background = sc["subtitleBackground"]
                if "items" in sc:
                    scene.items = sc["items"] or []
                if "cueTimings" in sc:
                    scene.cue_timings = sc["cueTimings"] or []
                if "subtitleSettings" in sc:
                    scene.subtitle_settings = sc["subtitleSettings"] or {}
                if "characters" in sc:
                    self._sync_scene_characters(db, scene.id, sc.get("characters") or [])
            db.commit()
            return self._get(db, story_id)

    @staticmethod
    def _sync_scene_characters(db: Session, scene_id: str, characters: list[dict]) -> None:
        """(scene,character) 기준 upsert + dict 에 없는 캐릭터 행 삭제(삽입 순서/created_at 보존)."""
        existing = db.execute(
            select(SceneCharacter).where(SceneCharacter.scene_id == scene_id)
        ).scalars().all()
        by_char = {c.character_id: c for c in existing}
        keep = set()
        for ch in characters:
            cid = ch.get("characterId")
            if not cid:
                continue
            keep.add(cid)
            row = by_char.get(cid)
            if row is None:
                db.add(SceneCharacter(
                    id=new_id("scene_character"),
                    scene_id=scene_id,
                    character_id=cid,
                    scene_appearance_prompt=ch.get("sceneAppearancePrompt"),
                    pose_id=ch.get("poseId"),
                    layout=ch.get("layout") or {},
                ))
            else:
                if "sceneAppearancePrompt" in ch:
                    row.scene_appearance_prompt = ch["sceneAppearancePrompt"]
                if "poseId" in ch:
                    row.pose_id = ch["poseId"]
                if ch.get("layout") is not None:
                    row.layout = ch["layout"]
        for cid, row in by_char.items():
            if cid not in keep:
                db.delete(row)

    # ── voiceLocks (대상별 잠금/TTS 토큰) ──────────────────────
    def lock_voice_target(self, story_id: str, target_id: str) -> int | None:
        with SessionLocal() as db:
            story = db.get(Story, story_id)
            if story is None:
                return None
            locks = dict(story.voice_locks or {})
            gen = (locks.get(target_id, {}).get("gen") or 0) + 1
            locks[target_id] = {"lockStatus": "locked", "ttsStatus": "generating", "gen": gen}
            story.voice_locks = locks
            db.commit()
            return gen

    def apply_target_tts_status(
        self, story_id: str, target_id: str, tts_status: str, expected_gen: int
    ) -> bool:
        with SessionLocal() as db:
            story = db.get(Story, story_id)
            if story is None:
                return False
            locks = dict(story.voice_locks or {})
            cur = locks.get(target_id)
            if not cur or cur.get("lockStatus") != "locked" or (cur.get("gen") or 0) != expected_gen:
                return False
            cur = {**cur, "ttsStatus": tts_status}
            locks[target_id] = cur
            story.voice_locks = locks
            db.commit()
            return True

    def unlock_voice_target(self, story_id: str, target_id: str) -> dict | None:
        with SessionLocal() as db:
            story = db.get(Story, story_id)
            if story is None:
                return None
            locks = dict(story.voice_locks or {})
            gen = locks.get(target_id, {}).get("gen") or 0
            locks[target_id] = {"lockStatus": "unlocked", "ttsStatus": "stale", "gen": gen}
            story.voice_locks = locks
            db.commit()
            return self._get(db, story_id)

    def get_voice_locks(self, story_id: str) -> dict:
        with SessionLocal() as db:
            story = db.get(Story, story_id)
            return (story.voice_locks or {}) if story else {}

    # ── narrator voice ───────────────────────────────────────
    def set_narrator_voice(self, story_id: str, voice_id: str | None) -> dict | None:
        with SessionLocal() as db:
            story = db.get(Story, story_id)
            if story is None:
                return None
            story.narrator_voice_id = voice_id
            db.commit()
            return self._get(db, story_id)

    def detach_narrator_voice(self, voice_id: str) -> None:
        """주어진 voiceId 를 나레이터로 쓰던 모든 story 의 narrator_voice_id 를 null 로(보이스 삭제 캐스케이드).

        DB FK 가 ondelete=SET NULL 이지만, 보이스 삭제 전 명시적 해제(대칭 유지)."""
        with SessionLocal() as db:
            from sqlalchemy import update as _update
            db.execute(
                _update(Story).where(Story.narrator_voice_id == voice_id).values(narrator_voice_id=None)
            )
            db.commit()

    # ── 렌더 결과(history; 최신 1건이 lastRender) ──────────────
    def set_last_render(self, story_id: str, last_render: dict | None) -> dict | None:
        """새 렌더 결과를 render_results 에 1건 추가한다(최신=lastRender). story 없으면 None.

        history 테이블이므로 last_render=None(해제) 은 의미가 없어 무시한다(현재 호출부 없음).
        """
        with SessionLocal() as db:
            story = db.get(Story, story_id)
            if story is None:
                return None
            if last_render:
                db.add(RenderResult(
                    id=last_render.get("renderId") or new_id("render"),
                    story_id=story_id,
                    video_url=last_render.get("videoUrl"),
                    duration=last_render.get("duration"),
                    status="completed",
                ))
                db.commit()
            return self._get(db, story_id)


story_repository = StoryRepository()

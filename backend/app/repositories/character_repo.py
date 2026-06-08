"""캐릭터 repository (PostgreSQL).

기존 in-memory 와 같은 메서드/반환(dict, camelCase + poses 임베디드)을 유지한다.
poses 는 character_poses 테이블(1:N)에 저장하고, get/list 시 character dict 의 "poses" 로 합쳐 반환.
ID = prefix+ULID. (마이그레이션 시에는 기존 ID를 그대로 넣을 수 있게 create(character_id, ...) 사용)
"""

from __future__ import annotations

from sqlalchemy import select, update

from ..core.ids import new_id
from ..db.models import Character, CharacterPose, SceneCharacter
from ..db.session import SessionLocal


def _pose_to_dict(p: CharacterPose) -> dict:
    # CharacterPoseResponse 와 동일 필드(characterId 필수). 누락 시 GET /poses 가 500.
    return {
        "poseId": p.id,
        "characterId": p.character_id,
        "posePrompt": p.prompt,
        "imageUrl": p.image_url,
    }


def _char_to_dict(c: Character, poses: list[CharacterPose]) -> dict:
    return {
        "characterId": c.id,
        "name": c.name,
        "appearancePrompt": c.appearance_prompt,
        "imageUrl": c.image_url,
        "voiceId": c.voice_id,
        "aiImagePath": c.ai_image_path,
        "poses": [_pose_to_dict(p) for p in poses],
    }


def _load_one(db, character_id: str) -> dict | None:
    c = db.get(Character, character_id)
    if c is None:
        return None
    poses = db.execute(
        select(CharacterPose).where(CharacterPose.character_id == character_id)
    ).scalars().all()
    return _char_to_dict(c, poses)


class CharacterRepository:
    def reserve_id(self) -> str:
        return new_id("character")

    def reserve_pose_id(self) -> str:
        return new_id("pose")

    def create(self, character_id: str, character_data: dict) -> dict:
        """예약된(또는 기존) characterId로 캐릭터 + (있으면) poses 저장."""
        with SessionLocal() as db:
            db.add(Character(
                id=character_id,
                name=character_data.get("name"),
                appearance_prompt=character_data.get("appearancePrompt"),
                image_url=character_data.get("imageUrl"),
                voice_id=character_data.get("voiceId"),
                ai_image_path=character_data.get("aiImagePath"),
                legacy_id=character_data.get("legacyId"),
            ))
            for pose in character_data.get("poses") or []:
                db.add(CharacterPose(
                    id=pose.get("poseId") or new_id("pose"),
                    character_id=character_id,
                    label=pose.get("label"),
                    prompt=pose.get("posePrompt"),
                    image_url=pose.get("imageUrl"),
                ))
            db.commit()
            return _load_one(db, character_id)

    def save(self, character_data: dict) -> dict:
        return self.create(self.reserve_id(), character_data)

    def list(self) -> list[dict]:
        with SessionLocal() as db:
            chars = db.execute(select(Character).order_by(Character.created_at)).scalars().all()
            poses = db.execute(select(CharacterPose)).scalars().all()
            by_char: dict[str, list] = {}
            for p in poses:
                by_char.setdefault(p.character_id, []).append(p)
            return [_char_to_dict(c, by_char.get(c.id, [])) for c in chars]

    def get(self, character_id: str) -> dict | None:
        with SessionLocal() as db:
            return _load_one(db, character_id)

    def update(self, character_id: str, update_data: dict) -> dict | None:
        with SessionLocal() as db:
            c = db.get(Character, character_id)
            if not c:
                return None
            # name/appearancePrompt: None(명시적 null)은 무시. imageUrl: 명시되면 set(null 허용).
            if "name" in update_data and update_data["name"] is not None:
                c.name = update_data["name"]
            if "appearancePrompt" in update_data and update_data["appearancePrompt"] is not None:
                c.appearance_prompt = update_data["appearancePrompt"]
            if "imageUrl" in update_data:
                c.image_url = update_data["imageUrl"]
            db.commit()
            return _load_one(db, character_id)

    def set_voice(self, character_id: str, voice_id: str | None) -> dict | None:
        with SessionLocal() as db:
            c = db.get(Character, character_id)
            if not c:
                return None
            c.voice_id = voice_id
            db.commit()
            return _load_one(db, character_id)

    def names_using_voice(self, voice_id: str) -> list[str]:
        """해당 voiceId 를 연결한 캐릭터 이름 목록(보이스 삭제 차단 판단/메시지용). 없으면 빈 리스트."""
        with SessionLocal() as db:
            rows = db.execute(
                select(Character.name).where(Character.voice_id == voice_id)
            ).scalars().all()
            return list(rows)

    def detach_voice(self, voice_id: str) -> int:
        """해당 voiceId 를 참조하던 모든 캐릭터의 voice_id 를 NULL 로(보이스 삭제 캐스케이드)."""
        with SessionLocal() as db:
            res = db.execute(
                update(Character).where(Character.voice_id == voice_id).values(voice_id=None)
            )
            db.commit()
            return res.rowcount or 0

    def delete(self, character_id: str) -> bool:
        with SessionLocal() as db:
            c = db.get(Character, character_id)
            if not c:
                return False
            db.delete(c)  # poses 는 FK ondelete=CASCADE
            db.commit()
            return True

    # ── 포즈 (1:N) ─────────────────────────────────────
    def add_pose(self, character_id: str, pose: dict) -> dict | None:
        with SessionLocal() as db:
            if db.get(Character, character_id) is None:
                return None
            db.add(CharacterPose(
                id=pose.get("poseId") or new_id("pose"),
                character_id=character_id,
                label=pose.get("label"),
                prompt=pose.get("posePrompt"),
                image_url=pose.get("imageUrl"),
            ))
            db.commit()
            return pose

    def list_poses(self, character_id: str) -> list | None:
        with SessionLocal() as db:
            if db.get(Character, character_id) is None:
                return None
            poses = db.execute(
                select(CharacterPose).where(CharacterPose.character_id == character_id)
            ).scalars().all()
            return [_pose_to_dict(p) for p in poses]

    def pose_in_use(self, pose_id: str) -> bool:
        """해당 포즈가 어떤 씬 캐릭터에 적용돼 있으면 True (삭제 차단 판단용)."""
        with SessionLocal() as db:
            return db.execute(
                select(SceneCharacter.id).where(SceneCharacter.pose_id == pose_id).limit(1)
            ).first() is not None

    def delete_pose(self, character_id: str, pose_id: str) -> bool:
        """캐릭터 소유의 포즈 1개 삭제. 없거나 다른 캐릭터 소유면 False."""
        with SessionLocal() as db:
            p = db.get(CharacterPose, pose_id)
            if p is None or p.character_id != character_id:
                return False
            db.delete(p)
            db.commit()
            return True


character_repository = CharacterRepository()

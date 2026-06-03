"""배경 라이브러리 repository (PostgreSQL).

기존 in-memory 와 같은 메서드/반환(dict, camelCase)을 유지한다. ID = prefix+ULID.
(마이그레이션 시 기존 ID를 그대로 넣을 수 있게 create(background_id, ...) 사용)
"""

from sqlalchemy import select

from ..core.ids import new_id
from ..db.models import Background
from ..db.session import SessionLocal


def _to_dict(b: Background) -> dict:
    return {
        "backgroundId": b.id,
        "name": b.name,
        "prompt": b.prompt,
        "finalPrompt": b.final_prompt,
        "imageUrl": b.image_url,
    }


class BackgroundRepository:
    def reserve_id(self) -> str:
        return new_id("background")

    def create(self, background_id: str, background_data: dict) -> dict:
        with SessionLocal() as db:
            db.add(Background(
                id=background_id,
                name=background_data.get("name"),
                prompt=background_data.get("prompt"),
                final_prompt=background_data.get("finalPrompt"),
                image_url=background_data.get("imageUrl"),
                legacy_id=background_data.get("legacyId"),
            ))
            db.commit()
            return _to_dict(db.get(Background, background_id))

    def save(self, background_data: dict) -> dict:
        return self.create(self.reserve_id(), background_data)

    def list(self) -> list[dict]:
        with SessionLocal() as db:
            rows = db.execute(select(Background).order_by(Background.created_at)).scalars().all()
            return [_to_dict(b) for b in rows]

    def get(self, background_id: str) -> dict | None:
        with SessionLocal() as db:
            b = db.get(Background, background_id)
            return _to_dict(b) if b else None

    def update(self, background_id: str, update_data: dict) -> dict | None:
        with SessionLocal() as db:
            b = db.get(Background, background_id)
            if not b:
                return None
            if update_data.get("name") is not None:  # MVP: name만 수정
                b.name = update_data["name"]
            db.commit()
            return _to_dict(b)

    def delete(self, background_id: str) -> bool:
        with SessionLocal() as db:
            b = db.get(Background, background_id)
            if not b:
                return False
            db.delete(b)
            db.commit()
            return True


background_repository = BackgroundRepository()

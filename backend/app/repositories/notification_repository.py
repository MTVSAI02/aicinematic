"""알림 repository (PostgreSQL).

job 완료/실패 알림을 저장/조회한다. 다른 repo 와 동일하게 dict(camelCase) 인터페이스.
중복 방지: (related_job_id, type) UNIQUE + on_conflict_do_nothing → job 1건당 알림 1건.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete as sa_delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ..core.ids import new_id
from ..db.models import Notification
from ..db.session import SessionLocal


def _iso(dt: datetime | None):
    return dt.isoformat() if dt else None


def _to_dict(n: Notification) -> dict:
    return {
        "id": n.id,
        "userId": n.user_id,
        "type": n.type,
        "title": n.title,
        "message": n.message,
        "relatedJobId": n.related_job_id,
        "relatedStoryId": n.related_story_id,
        "relatedSceneId": n.related_scene_id,
        "relatedTargetId": n.related_target_id,
        "isRead": n.is_read,
        "createdAt": _iso(n.created_at),
        "readAt": _iso(n.read_at),
    }


class NotificationRepository:
    def create(self, data: dict) -> dict | None:
        """알림 1건 생성. (related_job_id, type) 중복이면 생성하지 않고 None 반환."""
        with SessionLocal() as db:
            stmt = (
                pg_insert(Notification)
                .values(
                    id=new_id("notification"),
                    user_id=data.get("userId"),
                    type=data["type"],
                    title=data["title"],
                    message=data.get("message"),
                    related_job_id=data.get("relatedJobId"),
                    related_story_id=data.get("relatedStoryId"),
                    related_scene_id=data.get("relatedSceneId"),
                    related_target_id=data.get("relatedTargetId"),
                )
                .on_conflict_do_nothing(constraint="uq_notification_job_type")
                .returning(Notification.id)
            )
            new_pk = db.execute(stmt).scalar_one_or_none()
            db.commit()
            if new_pk is None:
                return None  # 중복(이미 같은 job+type 알림 존재)
            return _to_dict(db.get(Notification, new_pk))

    def list(self, limit: int = 50) -> list[dict]:
        with SessionLocal() as db:
            rows = db.execute(
                select(Notification).order_by(Notification.created_at.desc()).limit(limit)
            ).scalars().all()
            return [_to_dict(n) for n in rows]

    def unread_count(self) -> int:
        with SessionLocal() as db:
            return db.execute(
                select(func.count()).select_from(Notification).where(Notification.is_read.is_(False))
            ).scalar() or 0

    def mark_read(self, notification_id: str) -> dict | None:
        with SessionLocal() as db:
            n = db.get(Notification, notification_id)
            if n is None:
                return None
            if not n.is_read:
                n.is_read = True
                n.read_at = datetime.now(timezone.utc)
                db.commit()
                db.refresh(n)
            return _to_dict(n)

    def mark_all_read(self) -> int:
        with SessionLocal() as db:
            res = db.execute(
                update(Notification)
                .where(Notification.is_read.is_(False))
                .values(is_read=True, read_at=datetime.now(timezone.utc))
            )
            db.commit()
            return res.rowcount or 0

    def delete(self, notification_id: str) -> bool:
        """알림 1건 삭제. 없으면 False."""
        with SessionLocal() as db:
            n = db.get(Notification, notification_id)
            if n is None:
                return False
            db.delete(n)
            db.commit()
            return True

    def delete_all(self) -> int:
        """전체 알림 삭제. 삭제된 건수 반환."""
        with SessionLocal() as db:
            res = db.execute(sa_delete(Notification))
            db.commit()
            return res.rowcount or 0


notification_repository = NotificationRepository()

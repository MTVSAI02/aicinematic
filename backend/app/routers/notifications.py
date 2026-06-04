from fastapi import APIRouter, Query

from ..schemas.notification import (
    MarkAllReadResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from ..services.notification_service import notification_service

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse], summary="알림 목록 조회")
def list_notifications(limit: int = Query(50, ge=1, le=100, description="최대 100")):
    """최근 알림 목록(created_at desc). job 완료/실패 시 백엔드가 생성한 알림을 반환한다."""
    return notification_service.list_notifications(limit=limit)


@router.get("/unread-count", response_model=UnreadCountResponse, summary="읽지 않은 알림 개수")
def unread_count():
    return {"count": notification_service.unread_count()}


@router.patch("/read-all", response_model=MarkAllReadResponse, summary="전체 읽음 처리")
def mark_all_read():
    return notification_service.mark_all_read()


@router.patch("/{notification_id}/read", response_model=NotificationResponse, summary="단일 알림 읽음 처리")
def mark_read(notification_id: str):
    """존재하지 않으면 404(Notification not found)."""
    return notification_service.mark_read(notification_id)

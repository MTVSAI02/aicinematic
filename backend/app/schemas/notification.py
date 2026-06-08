from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    id: str = Field(description="notif_ + ULID")
    userId: str | None = Field(default=None, description="현재 전역 알림이라 보통 null")
    type: str = Field(description="예: render_completed / render_failed")
    title: str
    message: str | None = None
    relatedJobId: str | None = None
    relatedStoryId: str | None = None
    relatedSceneId: str | None = None
    relatedTargetId: str | None = Field(default=None, description="characterId/voiceId/backgroundId/renderId 등")
    isRead: bool
    createdAt: str | None = None
    readAt: str | None = None


class UnreadCountResponse(BaseModel):
    count: int


class MarkAllReadResponse(BaseModel):
    updated: int = Field(description="읽음 처리된 알림 수")


class DeleteAllResponse(BaseModel):
    deleted: int = Field(description="삭제된 알림 수")

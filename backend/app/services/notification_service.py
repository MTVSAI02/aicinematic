"""알림 비즈니스 로직.

핵심: job(완료/실패)을 받아 알림 1건을 생성한다. **알림 생성 규칙(대상 job·문구·관련 id)의 단일 출처.**
job_manager 가 job 완료/실패 직후 create_for_job() 을 호출한다(각 runner 는 안 건드림).
"""

import logging

from ..core.exceptions import NotificationNotFoundError
from ..repositories.notification_repository import notification_repository
from ..schemas.job import JobType

logger = logging.getLogger(__name__)

# 알림 대상 job_type → (completed/failed 별 notif type, 제목).
# 키는 JobType enum 값으로 묶어 enum 변경 시 누락을 막는다. character_pose_generate 는 1차 제외.
_JOB_NOTIF: dict[str, dict[str, tuple[str, str]]] = {
    JobType.character_generate.value: {
        "completed": ("character_completed", "캐릭터 생성 완료"),
        "failed": ("character_failed", "캐릭터 생성 실패"),
    },
    JobType.background_generate.value: {
        "completed": ("background_completed", "배경 생성 완료"),
        "failed": ("background_failed", "배경 생성 실패"),
    },
    JobType.voice_clone.value: {
        "completed": ("voice_completed", "보이스 생성 완료"),
        "failed": ("voice_failed", "보이스 생성 실패"),
    },
    JobType.tts_generate.value: {
        "completed": ("tts_completed", "음성 생성 완료"),
        "failed": ("tts_failed", "음성 생성 실패"),
    },
    JobType.tts_story_generate.value: {
        "completed": ("tts_completed", "음성 생성 완료"),
        "failed": ("tts_failed", "음성 생성 실패"),
    },
    JobType.render_generate.value: {
        "completed": ("render_completed", "영상 생성 완료"),
        "failed": ("render_failed", "영상 생성 실패"),
    },
}

_DONE_MESSAGE = {
    "character_completed": "캐릭터 생성이 완료되었습니다.",
    "background_completed": "배경 생성이 완료되었습니다.",
    "voice_completed": "보이스 생성이 완료되었습니다.",
    "tts_completed": "음성 생성이 완료되었습니다.",
    "render_completed": "영상 생성이 완료되었습니다.",
    "character_failed": "캐릭터 생성에 실패했습니다.",
    "background_failed": "배경 생성에 실패했습니다.",
    "voice_failed": "보이스 생성에 실패했습니다.",
    "tts_failed": "음성 생성에 실패했습니다.",
    "render_failed": "영상 생성에 실패했습니다.",
}


class NotificationService:
    def __init__(self, repo):
        self._repo = repo

    # ── job 완료/실패 시 알림 생성 (job_manager 가 호출) ──────────────
    def create_for_job(self, job: dict | None) -> dict | None:
        """job(type/status/result/payload)으로 알림 1건 생성. 대상 아니면 None.

        실패해도 절대 예외를 올리지 않는다(알림이 job 처리를 깨면 안 됨).
        """
        try:
            if not job:
                return None
            mapping = _JOB_NOTIF.get(job.get("type"))
            if not mapping:
                return None  # 알림 대상 job 아님
            spec = mapping.get(job.get("status"))
            if not spec:
                return None  # completed/failed 외 상태
            notif_type, title = spec

            payload = job.get("payload") or {}
            result = job.get("result") or {}
            related_target = (
                result.get("characterId")
                or result.get("voiceId")
                or result.get("backgroundId")
                or result.get("renderId")
                or payload.get("targetId")  # 실패 시 result 없음 → payload 로 대상 id 보존
            )
            return self._repo.create(
                {
                    "type": notif_type,
                    "title": title,
                    "message": _DONE_MESSAGE.get(notif_type, title),
                    "relatedJobId": job.get("jobId"),
                    "relatedStoryId": payload.get("storyId") or result.get("storyId"),
                    "relatedSceneId": payload.get("sceneId") or result.get("sceneId"),
                    "relatedTargetId": related_target,
                }
            )
        except Exception as exc:  # noqa: BLE001 — 알림 생성 실패가 job 처리를 깨지 않게
            # 단, 조용히 삼키지 않고 원인 추적용 warning 은 남긴다(마이그레이션 누락/제약 오류 등).
            logger.warning("알림 생성 실패 (job=%s): %s", (job or {}).get("jobId"), exc)
            return None

    # ── 조회/읽음 (API) ──────────────────────────────────────────────
    def list_notifications(self, limit: int = 50) -> list[dict]:
        return self._repo.list(limit=limit)

    def unread_count(self) -> int:
        return self._repo.unread_count()

    def mark_read(self, notification_id: str) -> dict:
        updated = self._repo.mark_read(notification_id)
        if updated is None:
            raise NotificationNotFoundError()
        return updated

    def mark_all_read(self) -> dict:
        count = self._repo.mark_all_read()
        return {"updated": count}

    def delete_notification(self, notification_id: str) -> None:
        if not self._repo.delete(notification_id):
            raise NotificationNotFoundError()

    def delete_all_notifications(self) -> dict:
        return {"deleted": self._repo.delete_all()}


notification_service = NotificationService(notification_repository)

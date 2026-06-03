"""영상 렌더링 orchestration.

- 동기(요청 안에서): render plan 생성·검증 → story 없음 404 / plan 비었으면 400 을 바로 반환.
- 비동기(Job): renderId 발급 → ffmpeg_render_service 로 무음 mp4 생성 → story.lastRender 저장 → result 반환.
- 렌더러는 render plan 결과만 입력으로 받는다(여기서 plan 을 스냅샷으로 캡처해 넘긴다).
- 스토리당 최신 렌더 1개만 기억한다(새 렌더가 lastRender 를 덮고, 이전 mp4 는 정리).
"""

import os
import uuid
from datetime import datetime, timezone

from ..core.config import RENDER_STORAGE_DIR, storage_path
from ..core.exceptions import (
    FFmpegRenderFailedError,
    RenderAudioNotReadyError,
    RenderPlanInvalidError,
    StoryNotFoundError,
)
from ..repositories.story_repo import story_repository
from ..schemas.job import JobType
from . import voice_lock_service
from .ffmpeg_render_service import render_video
from .job_manager import job_manager
from .timeline_service import timeline_service


def _validate_audio_ready(story_id: str, plan: dict) -> None:
    """렌더 전 음성 준비 검증(실패 시 400). 무음이 아니라 TTS 포함 영상이므로 음성이 갖춰져야 한다.

    1) 모든 필수 보이스 locked + 실패 대상 없음(nextStepEnabled)
    2) cue.items 중 audioUrl 없는 item 없음
    3) audioUrl 파일이 storage 에 실제 존재
    (씬 길이 vs 음성 길이 불일치는 -shortest + 타임라인 '음성 길이에 맞추기'로 처리 — 여기선 막지 않음)
    """
    locks = voice_lock_service.get_voice_locks(story_id)
    if not locks.get("nextStepEnabled"):
        raise RenderAudioNotReadyError(
            "보이스 설정이 완료되지 않았습니다. 보이스 페이지에서 모든 목소리를 연결·잠그고 음성 생성을 마쳐 주세요."
        )
    for scene in plan.get("scenes") or []:
        for cue in scene.get("cueTimings") or []:
            for item in cue.get("items") or []:
                url = item.get("audioUrl")
                path = storage_path(url) if url else None
                if not url or path is None or not path.exists():
                    raise RenderAudioNotReadyError()


def _persist_dev_snapshot() -> None:
    """렌더 잡은 HTTP 요청 밖(백그라운드 스레드)에서 끝나 dev_persist 미들웨어가 안 잡는다.

    SEED_DEV 면 직접 스냅샷을 저장해 재시작 후에도 story.lastRender 가 유지되게 한다.
    """
    if os.getenv("SEED_DEV") == "1":
        try:
            from ..core.dev_persist import save_snapshot

            save_snapshot()
        except Exception:  # noqa: BLE001 (스냅샷 실패가 렌더 성공을 깨지 않게)
            pass


def create_render_job(story_id: str) -> dict:
    # 동기 검증: story 없음 → StoryNotFoundError(404). plan 비었으면 → RenderPlanInvalidError(400).
    plan = timeline_service.build_render_plan(story_id)
    if not plan.get("scenes"):
        raise RenderPlanInvalidError()
    # 음성 포함 영상 — 렌더 전 TTS 준비 검증(미완료/누락 → 400)
    _validate_audio_ready(story_id, plan)

    render_id = f"render_{uuid.uuid4().hex[:12]}"

    def build_result() -> dict:
        video_url = render_video(render_id, plan)
        duration = round(float(plan.get("totalDuration") or 0.0), 3)

        # 이전 렌더(있으면)를 기억해 두고 lastRender 를 새 결과로 덮어쓴다.
        story = story_repository.get(story_id)
        prev = (story or {}).get("lastRender")
        story_repository.set_last_render(
            story_id,
            {
                "renderId": render_id,
                "videoUrl": video_url,
                "duration": duration,
                "createdAt": datetime.now(timezone.utc).isoformat(),
            },
        )
        _persist_dev_snapshot()  # 백그라운드 완료분을 스냅샷에 반영(재시작 유지)

        # 스토리당 최신 1개 유지: 이전 mp4 정리(실패해도 무시)
        if prev and prev.get("renderId") and prev["renderId"] != render_id:
            (RENDER_STORAGE_DIR / f"{prev['renderId']}.mp4").unlink(missing_ok=True)

        return {"renderId": render_id, "storyId": story_id, "videoUrl": video_url, "duration": duration}

    return job_manager.run_async(
        JobType.render_generate.value,
        build_result,
        FFmpegRenderFailedError.detail,
        "Render job started.",
    )


def get_last_render(story_id: str) -> dict:
    """스토리의 최신 렌더 결과. 없으면 lastRender=None. 없는 story → 404."""
    story = story_repository.get(story_id)
    if story is None:
        raise StoryNotFoundError()
    return {"storyId": story_id, "lastRender": story.get("lastRender")}

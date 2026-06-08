"""영상 렌더링 orchestration.

- 동기(요청 안에서): render plan 생성·검증 → story 없음 404 / plan 비었으면 400 을 바로 반환.
- 비동기(Job): renderId 발급 → ffmpeg_render_service 로 무음 mp4 생성 → story.lastRender 저장 → result 반환.
- 렌더러는 render plan 결과만 입력으로 받는다(여기서 plan 을 스냅샷으로 캡처해 넘긴다).
- 스토리당 최신 렌더 1개만 기억한다(새 렌더가 lastRender 를 덮고, 이전 mp4 는 정리).
"""

import logging
import uuid
from datetime import datetime, timezone

from ..core import storage
from ..core.config import RENDER_FPS
from ..core.exceptions import (
    FFmpegRenderFailedError,
    RenderAudioNotReadyError,
    RenderInProgressError,
    RenderPlanInvalidError,
    StoryNotFoundError,
)
from ..repositories.job_repo import job_repository
from ..repositories.story_repo import story_repository
from ..schemas.job import JobType
from . import voice_lock_service
from .ffmpeg_render_service import render_video
from .job_manager import job_manager
from .timeline_service import timeline_service

logger = logging.getLogger(__name__)


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
                # storage(R2/로컬) 에 실제 객체가 있는지 검증 — 로컬 경로 직접 접근 대신 key 기준.
                if not url or not storage.exists(storage.storage_url_to_key(url)):
                    raise RenderAudioNotReadyError()


def cleanup_unfinished_render_jobs() -> int:
    """서버 재시작으로 in-memory 워커가 사라졌는데 DB에 pending/running 으로 남은 렌더 job 을 failed 로 정리.

    렌더는 plan 스냅샷이 사라져 안전 재개가 불가하므로 실패로 표시해 프론트 폴링이 멈추게 한다.
    (안 하면 유령 'running' job 이 동시 1개 가드를 막아 새 렌더도 못 돌린다.)
    """
    n = 0
    for job in job_repository.list_unfinished(JobType.render_generate.value):
        jid = job.get("jobId")
        if jid:
            job_repository.fail(jid, "서버 재시작으로 렌더가 중단되었습니다. 다시 시도해 주세요.")
            n += 1
    if n:
        logger.info("미완료 렌더 job %d개 정리(failed) — 서버 재시작 복구", n)
    return n


def create_render_job(story_id: str) -> dict:
    # 동기 검증: story 없음 → StoryNotFoundError(404). plan 비었으면 → RenderPlanInvalidError(400).
    plan = timeline_service.build_render_plan(story_id)
    if not plan.get("scenes"):
        raise RenderPlanInvalidError()
    # 음성 포함 영상 — 렌더 전 TTS 준비 검증(미완료/누락 → 400)
    _validate_audio_ready(story_id, plan)

    # 동시 렌더 1개 제한: 이미 진행 중(pending/running)인 렌더가 있으면 거절(409). 서버/WSL 과부하 방지.
    if job_repository.list_unfinished(JobType.render_generate.value):
        raise RenderInProgressError()

    # 렌더 규모 로깅(디버깅/모니터링용): 총 길이 / fps / 총 프레임.
    total_duration = round(float(plan.get("totalDuration") or 0.0), 1)
    total_frames = max(1, round(total_duration * RENDER_FPS))
    logger.info(
        "렌더 시작 story=%s scenes=%d total=%.1fs fps=%d total_frames=%d",
        story_id, len(plan.get("scenes") or []), total_duration, RENDER_FPS, total_frames,
    )

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

        # 스토리당 최신 1개 유지: 이전 mp4 정리(없어도 무시). storage(R2/로컬) 경유.
        if prev and prev.get("renderId") and prev["renderId"] != render_id:
            storage.delete(f"renders/{prev['renderId']}.mp4")

        return {"renderId": render_id, "storyId": story_id, "videoUrl": video_url, "duration": duration}

    return job_manager.run_async(
        JobType.render_generate.value,
        build_result,
        FFmpegRenderFailedError.detail,
        "Render job started.",
        payload={"storyId": story_id},  # 실패 알림도 storyId 보존(클릭→해당 영상/스토리 이동)
    )


def get_last_render(story_id: str) -> dict:
    """스토리의 최신 렌더 결과. 없으면 lastRender=None. 없는 story → 404."""
    story = story_repository.get(story_id)
    if story is None:
        raise StoryNotFoundError()
    return {"storyId": story_id, "lastRender": story.get("lastRender")}

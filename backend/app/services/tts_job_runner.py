from ..core.exceptions import TTSGenerationFailedError
from ..repositories.job_repo import job_repository
from ..schemas.job import JobStatus, JobType
from .job_manager import job_manager


def create_tts_generation_job(
    story_id: str, scene_id: str, audios: list[dict]
) -> dict:
    """이미 생성/저장된 audios로 tts_generate Job (즉시 completed).

    audio 생성/저장은 TTSService가 담당하고, 여기서는 Job 결과만 구성한다.
    """

    def build_result() -> dict:
        return {"storyId": story_id, "sceneId": scene_id, "audios": audios}

    return job_manager.run(
        JobType.tts_generate.value,
        build_result,
        TTSGenerationFailedError.detail,
        "TTS generation job completed.",
    )


def create_tts_story_generation_job(story_id: str, build_result) -> dict:
    """Run story-wide TTS generation in the background.

    동일 storyId + pending/running 상태의 tts_story_generate job이 이미 있으면
    새 job을 만들지 않고 기존 job을 반환한다(중복 생성 방지).
    """
    existing = [
        j for j in job_repository.list_unfinished(JobType.tts_story_generate.value)
        if j.get("storyId") == story_id
        or (j.get("payload") or {}).get("storyId") == story_id
    ]
    if existing:
        job = existing[-1]  # 가장 최근 pending/running job
        return {
            "jobId": job["jobId"],
            "status": job["status"],
            "message": "이미 TTS 생성 중인 job이 있습니다.",
        }

    return job_manager.run_async(
        JobType.tts_story_generate.value,
        build_result,
        TTSGenerationFailedError.detail,
        "Story TTS generation job accepted.",
        payload={"storyId": story_id},
    )

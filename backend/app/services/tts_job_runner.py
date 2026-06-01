from ..core.exceptions import TTSGenerationFailedError
from ..schemas.job import JobType
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

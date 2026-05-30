from ..core.exceptions import CharacterGenerationFailedError
from ..repositories.character_repo import character_repository
from ..schemas.job import JobType
from .job_manager import job_manager


def create_character_generation_job(request_data: dict) -> dict:
    """캐릭터 생성 Job (mock, 즉시 completed). 이미지 생성은 ComfyUI 파트 담당이므로 imageUrl=None."""

    def build_result() -> dict:
        # mock 캐릭터 저장 (characterId 발급) → Job result로 사용
        return character_repository.save(
            {
                "name": request_data.get("name"),
                "appearancePrompt": request_data.get("appearancePrompt"),
                "imageUrl": None,
            }
        )

    return job_manager.run(
        JobType.character_generate.value,
        build_result,
        CharacterGenerationFailedError.detail,
        "Character generation job completed with mock result.",
    )

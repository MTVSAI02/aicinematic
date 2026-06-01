from ai.character_ctrl.character import generate_character

from ..core.exceptions import CharacterGenerationFailedError
from ..repositories.character_repo import character_repository
from ..schemas.job import JobType
from .job_manager import job_manager


def create_character_generation_job(request_data: dict) -> dict:
    """캐릭터 생성 Job — ComfyUI(HiDream-O1)로 실제 이미지를 생성한다."""

    def build_result() -> dict:
        # 1. 캐릭터 레코드 저장 (characterId 발급)
        character = character_repository.save(
            {
                "name": request_data.get("name"),
                "appearancePrompt": request_data.get("appearancePrompt"),
                "imageUrl": None,
            }
        )
        character_id = character["characterId"]

        # 2. ComfyUI로 이미지 생성 → storage에 저장
        image_path = generate_character(
            character_id=character_id,
            name=character["name"],
            appearance_prompt=character["appearancePrompt"],
        )

        # 3. imageUrl 업데이트 (프론트가 접근할 수 있는 경로)
        image_url = f"/storage/characters/{character_id}.png"
        updated = character_repository.update(character_id, {"imageUrl": image_url})
        return updated

    return job_manager.run(
        JobType.character_generate.value,
        build_result,
        CharacterGenerationFailedError.detail,
        "Character generation completed.",
    )

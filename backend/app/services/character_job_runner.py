from ai.character_ctrl.character import generate_character

from ..core.config import storage_url
from ..core.exceptions import CharacterGenerationFailedError
from ..repositories.character_repo import character_repository
from ..schemas.job import JobType
from .job_manager import job_manager


def create_character_generation_job(request_data: dict) -> dict:
    """캐릭터 생성 Job — ComfyUI(HiDream-O1)로 실제 이미지를 생성한다. (비동기)

    jobId를 즉시 반환하고 생성은 백그라운드에서 진행된다.
    프론트는 GET /api/jobs/{jobId}로 pending→running→completed/failed를 폴링한다.
    """

    def build_result() -> dict:
        # 1. characterId만 먼저 발급(저장 X) — 생성 실패 시 orphan 방지
        character_id = character_repository.reserve_id()
        name = request_data.get("name")
        appearance_prompt = request_data.get("appearancePrompt")
        description = request_data.get("description")  # 저장용 메타데이터(ComfyUI엔 안 넘김)

        # 2. ComfyUI로 이미지 생성. 실패하면 예외 → record 저장 안 됨 → orphan 없음.
        #    생성 prompt는 appearancePrompt만 사용한다(description은 표시용 메타라 미사용).
        #    ⚠️ 임시안: 현재는 AI 모듈이 storage에 직접 저장한다.
        #    2차 정석(저장 경계 계약): AI는 bytes만 반환, backend가 저장하도록 전환 예정.
        generate_character(
            character_id=character_id,
            name=name,
            appearance_prompt=appearance_prompt,
        )

        # 3. 생성 성공 → imageUrl 채워서 비로소 record 저장 (경로는 config에서 관리)
        image_url = storage_url("characters", f"{character_id}.png")
        return character_repository.create(
            character_id,
            {
                "name": name,
                "appearancePrompt": appearance_prompt,
                "description": description,
                "imageUrl": image_url,
            },
        )

    return job_manager.run_async(
        JobType.character_generate.value,
        build_result,
        CharacterGenerationFailedError.detail,
        "Character generation job accepted.",
    )

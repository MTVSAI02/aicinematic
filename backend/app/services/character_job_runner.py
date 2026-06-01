from ..core.config import CHARACTER_STORAGE_DIR, storage_url
from ..core.exceptions import CharacterGenerationFailedError
from ..repositories.character_repo import character_repository
from ..schemas.job import JobType
from .ai_character_client import generate_character_image
from .character_service import build_character_final_prompt
from .job_manager import job_manager


def create_character_generation_job(request_data: dict) -> dict:
    """캐릭터 생성 Job (비동기).

    구조: Backend → 우리 AI FastAPI 서버(/generate-character) → 외부 ComfyUI.
    Backend는 ComfyUI를 직접 호출하지 않고, appearancePrompt로 finalPrompt를 만들어
    AI 서버에 `{prompt}`로만 보낸다. seed/steps/cfg/model/width/height/negativePrompt는
    backend가 다루지 않는다(AI 서버/워크플로 내부 책임).

    jobId를 즉시 반환하고 생성은 백그라운드에서 진행된다.
    프론트는 GET /api/jobs/{jobId}로 pending→running→completed/failed를 폴링한다.
    """

    def build_result() -> dict:
        # 1. characterId만 먼저 발급(저장 X) — 생성 실패 시 orphan 방지
        character_id = character_repository.reserve_id()
        name = request_data.get("name")
        appearance_prompt = request_data.get("appearancePrompt")
        description = request_data.get("description")  # 저장용 메타데이터(생성 prompt엔 안 넘김)

        # 2. 최종 prompt 조립(description 제외) → AI 서버 1회 호출 → 이미지 bytes 수신.
        #    실패하면 예외 → 파일/record 저장 안 됨 → orphan 없음.
        final_prompt = build_character_final_prompt(appearance_prompt)
        image_bytes = generate_character_image(final_prompt)  # AI 서버에는 {"prompt": final_prompt}

        # 3. 저장은 backend 담당: storage 파일 저장 → /storage URL → record 저장
        CHARACTER_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        (CHARACTER_STORAGE_DIR / f"{character_id}.png").write_bytes(image_bytes)
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

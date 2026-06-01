from ..core.config import BACKGROUND_CANDIDATE_STORAGE_DIR, storage_url
from ..core.exceptions import BackgroundGenerationFailedError
from ..repositories.background_candidate_repository import background_candidate_repository
from ..schemas.job import JobType
from .ai_background_client import generate_background_images
from .background_service import assemble_final_prompt
from .job_manager import job_manager


def create_background_generation_job(request_data: dict) -> dict:
    """배경 후보 생성 Job (비동기).

    구조: Backend → 우리 AI FastAPI 서버(/generate) → 외부 ComfyUI.
    Backend는 ComfyUI를 직접 호출하지 않고, finalPrompt를 만들어 AI 서버에 `{prompt}`로만 보낸다.
    negativePrompt는 backend가 다루지 않는다(AI 서버/워크플로 내부 고정값).

    AI 서버 1회 호출 → ComfyUI batch 결과(여러 장)를 받아 backend가 storage에 저장한다.
    후보 개수는 백엔드가 정하지 않고 **AI/ComfyUI가 돌려준 만큼** 저장한다.
    jobId 즉시 반환 → 프론트가 GET /api/jobs/{jobId} 폴링.
    """

    def build_result() -> dict:
        prompt = request_data.get("prompt")
        final_prompt = assemble_final_prompt(prompt)  # prompt + 배경 suffix (내부 개념)

        # 1. AI 서버 1회 호출 → 이미지 bytes 목록 (실패하면 예외 → Job failed, 부분 저장 없음)
        images = generate_background_images(final_prompt)  # AI 서버에는 {"prompt": final_prompt}

        # 2. 저장은 backend 담당: 받은 만큼 candidate별로 파일 저장 + imageUrl 생성
        BACKGROUND_CANDIDATE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        candidates = []
        for image_bytes in images:
            candidate_id = background_candidate_repository.reserve_id()
            (BACKGROUND_CANDIDATE_STORAGE_DIR / f"{candidate_id}.png").write_bytes(image_bytes)
            image_url = storage_url("backgrounds", "candidates", f"{candidate_id}.png")
            background_candidate_repository.create(
                candidate_id,
                {"prompt": prompt, "finalPrompt": final_prompt, "imageUrl": image_url},
            )
            candidates.append({"candidateId": candidate_id, "imageUrl": image_url})

        return {
            "prompt": prompt,
            "finalPrompt": final_prompt,
            "candidates": candidates,
        }

    return job_manager.run_async(
        JobType.background_generate.value,
        build_result,
        BackgroundGenerationFailedError.detail,
        "Background generation job accepted.",
    )

from ..core.exceptions import BackgroundGenerationFailedError
from ..repositories.background_candidate_repository import background_candidate_repository
from ..schemas.job import JobType
from .background_service import assemble_final_prompt, resolve_negative_prompt
from .job_manager import job_manager

# mock 후보 개수. 실제로는 ComfyUI 워크플로가 몇 장 생성할지 결정한다.
# 백엔드가 정하는 값이 아니라, 현재 mock 단계에서 "ComfyUI가 4장을 돌려준다"고 가정한 값일 뿐이다.
MOCK_BACKGROUND_CANDIDATE_COUNT = 4


def create_background_generation_job(request_data: dict) -> dict:
    """배경 후보 생성 Job (비동기). 캐릭터와 동일하게 jobId를 즉시 반환하고

    생성은 백그라운드에서 진행된다(실제 ComfyUI 연동 대비). 프론트는 GET /api/jobs/{jobId}로
    폴링한다. 현재는 mock 후보(imageUrl=None)를 만든다."""

    def build_result() -> dict:
        prompt = request_data.get("prompt")
        final_prompt = assemble_final_prompt(prompt)
        negative_prompt = resolve_negative_prompt(request_data.get("negativePrompt"))

        # 후보 개수는 백엔드가 정하지 않는다(실제로는 ComfyUI가 생성한 만큼).
        candidates = []
        for _ in range(MOCK_BACKGROUND_CANDIDATE_COUNT):
            candidates.append(
                background_candidate_repository.save(
                    {
                        "prompt": prompt,
                        "finalPrompt": final_prompt,
                        "negativePrompt": negative_prompt,
                        "imageUrl": None,
                    }
                )
            )

        # result.candidates 에는 candidateId/imageUrl 만 노출
        return {
            "prompt": prompt,
            "finalPrompt": final_prompt,
            "negativePrompt": negative_prompt,
            "candidates": [
                {"candidateId": c["candidateId"], "imageUrl": c["imageUrl"]}
                for c in candidates
            ],
        }

    return job_manager.run_async(
        JobType.background_generate.value,
        build_result,
        BackgroundGenerationFailedError.detail,
        "Background generation job accepted.",
    )

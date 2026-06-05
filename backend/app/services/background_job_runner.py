from ..core.exceptions import BackgroundGenerationFailedError
from ..schemas.job import JobType
from .ai_background_client import generate_background_images
from .background_service import assemble_final_prompt, background_service
from .job_manager import job_manager


def create_background_generation_job(request_data: dict) -> dict:
    """배경 생성 Job (비동기).

    구조: Backend → 우리 AI FastAPI 서버(/generate) → 외부 ComfyUI.
    Backend는 ComfyUI를 직접 호출하지 않고, finalPrompt를 만들어 AI 서버에 `{prompt}`로만 보낸다.
    negativePrompt는 backend가 다루지 않는다(AI 서버/워크플로 내부 고정값).

    **1장만 생성 → 곧바로 라이브러리에 저장**한다(후보·선택·이름 입력 단계 없음).
    AI/ComfyUI가 여러 장을 돌려줘도 첫 장만 사용한다(batch=1 권장). 이름은 prompt 로 자동 지정.
    jobId 즉시 반환 → 프론트가 GET /api/jobs/{jobId} 폴링 → completed 시 result.background.
    """

    def build_result() -> dict:
        prompt = (request_data.get("prompt") or "").strip()
        final_prompt = assemble_final_prompt(prompt)  # prompt + 배경 suffix (내부 개념)

        # 1. AI 서버 1회 호출 → 이미지 bytes 목록 (실패하면 예외 → Job failed, 저장 없음)
        images = generate_background_images(final_prompt)  # AI 서버에는 {"prompt": final_prompt}
        if not images:
            raise BackgroundGenerationFailedError()

        # 2. 첫 장만 사용해 곧바로 라이브러리에 저장(이름=prompt 자동). 후보 단계 없음.
        saved = background_service.save_generated_background(
            images[0], prompt=prompt, final_prompt=final_prompt, name=prompt
        )

        return {
            "prompt": prompt,
            "finalPrompt": final_prompt,
            "background": saved,
        }

    return job_manager.run_async(
        JobType.background_generate.value,
        build_result,
        BackgroundGenerationFailedError.detail,
        "Background generation job accepted.",
    )

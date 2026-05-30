from ..core.exceptions import (
    BackgroundGenerationFailedError,
    CharacterGenerationFailedError,
)
from ..repositories.background_candidate_repository import background_candidate_repository
from ..repositories.character_repo import character_repository
from ..repositories.job_repo import job_repository
from ..schemas.job import JobStatus, JobType
from .background_service import assemble_final_prompt, resolve_negative_prompt

# mock 후보 개수. 실제로는 ComfyUI 워크플로가 몇 장 생성할지 결정한다.
# 백엔드가 정하는 값이 아니라, 현재 mock 단계에서 "ComfyUI가 4장을 돌려준다"고 가정한 값일 뿐이다.
MOCK_BACKGROUND_CANDIDATE_COUNT = 4


class InMemoryJobManager:
    """캐릭터 생성 Job을 메모리에서 즉시 처리하는 Mock JobManager.

    이번 단계에서는 RabbitMQ/Celery/ComfyUI 연동 없이 mock 결과를 만들어
    Job을 즉시 completed 처리한다.

    나중에 이 클래스만 RabbitMQ/Celery publish 버전으로 교체하면 된다.
        현재: FastAPI -> InMemoryJobManager -> Mock Character Result
        나중: FastAPI -> RabbitMQ/Celery -> Worker -> ComfyUI -> Character Result
    라우터가 직접 Job 상태를 만들거나 character_repo를 조작하지 않도록
    생성 흐름 전체를 이 매니저가 담당한다.
    """

    def __init__(self, job_repo, character_repo, background_candidate_repo):
        self._job_repo = job_repo
        self._character_repo = character_repo
        self._background_candidate_repo = background_candidate_repo

    def create_character_generation_job(self, request_data: dict) -> dict:
        # 1. Job 생성 (pending)
        job = self._job_repo.create(JobType.character_generate.value)
        job_id = job["jobId"]

        # 2. running 으로 전환
        self._job_repo.update_status(job_id, JobStatus.running.value, progress=10)

        try:
            # 3. mock 캐릭터 결과 생성 (이미지 생성은 ComfyUI 파트 담당이므로 imageUrl=None)
            mock_character = {
                "name": request_data.get("name"),
                "appearancePrompt": request_data.get("appearancePrompt"),
                "imageUrl": None,
            }

            # 4. Character Repository에 저장 (characterId 발급)
            saved_character = self._character_repo.save(mock_character)

            # 5. Job 완료 처리 (result에 캐릭터 정보 포함, progress=100)
            self._job_repo.complete(job_id, result=saved_character)
        except Exception:  # noqa: BLE001
            # 나중에 RabbitMQ/Celery/ComfyUI로 교체될 때를 대비해 실패 상태를 표현한다.
            # Job은 failed 상태 + error 메시지로 저장하고, 클라이언트는
            # GET /api/jobs/{job_id}로 failed 상태를 확인한다.
            self._job_repo.fail(job_id, CharacterGenerationFailedError.detail)
            return {
                "jobId": job_id,
                "status": JobStatus.failed.value,
                "message": CharacterGenerationFailedError.detail,
            }

        # 6. 클라이언트에는 jobId / status / message 반환
        return {
            "jobId": job_id,
            "status": JobStatus.completed.value,
            "message": "Character generation job completed with mock result.",
        }

    def create_background_generation_job(self, request_data: dict) -> dict:
        # 1. Job 생성 (pending)
        job = self._job_repo.create(JobType.background_generate.value)
        job_id = job["jobId"]

        # 2. running 으로 전환
        self._job_repo.update_status(job_id, JobStatus.running.value, progress=10)

        try:
            prompt = request_data.get("prompt")
            final_prompt = assemble_final_prompt(prompt)
            negative_prompt = resolve_negative_prompt(request_data.get("negativePrompt"))

            # 3. mock 후보 생성 (이미지 생성은 ComfyUI 파트 담당이므로 imageUrl=None)
            #    후보 개수는 백엔드가 정하지 않는다. 실제로는 ComfyUI가 생성한 만큼 받게 되며,
            #    여기서는 mock으로 그 결과를 흉내내 MOCK_BACKGROUND_CANDIDATE_COUNT 장을 만든다.
            candidates = []
            for _ in range(MOCK_BACKGROUND_CANDIDATE_COUNT):
                candidate = self._background_candidate_repo.save(
                    {
                        "prompt": prompt,
                        "finalPrompt": final_prompt,
                        "negativePrompt": negative_prompt,
                        "imageUrl": None,
                    }
                )
                candidates.append(candidate)

            # 4. Job 완료 처리 (result.candidates 에는 candidateId/imageUrl 만 노출)
            result = {
                "prompt": prompt,
                "finalPrompt": final_prompt,
                "negativePrompt": negative_prompt,
                "candidates": [
                    {"candidateId": c["candidateId"], "imageUrl": c["imageUrl"]}
                    for c in candidates
                ],
            }
            self._job_repo.complete(job_id, result=result)
        except Exception:  # noqa: BLE001
            self._job_repo.fail(job_id, BackgroundGenerationFailedError.detail)
            return {
                "jobId": job_id,
                "status": JobStatus.failed.value,
                "message": BackgroundGenerationFailedError.detail,
            }

        return {
            "jobId": job_id,
            "status": JobStatus.completed.value,
            "message": "Background generation job completed with mock candidates.",
        }


job_manager = InMemoryJobManager(
    job_repository,
    character_repository,
    background_candidate_repository,
)

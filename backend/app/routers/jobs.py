from fastapi import APIRouter

from ..schemas.job import JobResponse
from ..services.job_service import job_service

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobResponse, summary="Job 상태 조회")
def get_job(job_id: str):
    """
    비동기 작업(Job) 상태를 조회합니다.

    - type: `character_generate` / `background_generate` / `tts_generate`
    - jobId 예시: `job_mock_001`
    - status: `pending`, `running`, `completed`, `failed`
    - 존재하지 않는 jobId 요청 시 404(`Job not found`)를 반환합니다.

    캐릭터/배경 생성은 **비동기**라 `pending`→`running`→`completed/failed`로 진행됩니다.
    클라이언트는 이 엔드포인트를 폴링해 `completed`면 `result`, `failed`면 `error`를 확인합니다.
    (씬 TTS는 동기 Job이라 즉시 `completed`)
    """
    return job_service.get_job(job_id)

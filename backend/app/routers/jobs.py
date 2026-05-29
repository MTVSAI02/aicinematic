from fastapi import APIRouter

from ..schemas.job import JobResponse
from ..services.job_service import job_service

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobResponse, summary="Job 상태 조회")
def get_job(job_id: str):
    """
    캐릭터 생성 작업의 상태를 조회합니다.

    - jobId 예시: `job_mock_001`
    - status: `pending`, `running`, `completed`, `failed`
    - 존재하지 않는 jobId 요청 시 404(`Job not found`)를 반환합니다.

    현재 단계는 mock 구현이라 생성 직후 바로 `completed` 상태가 됩니다.
    """
    return job_service.get_job(job_id)

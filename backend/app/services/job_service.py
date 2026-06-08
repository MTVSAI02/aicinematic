from ..core.exceptions import JobNotFoundError
from ..repositories.job_repo import job_repository


class JobService:
    """Job 조회 비즈니스 로직.

    존재하지 않는 Job은 JobNotFoundError로 변환하고,
    HTTP 응답 변환은 글로벌 exception handler가 담당한다.
    """

    def __init__(self, job_repo):
        self._job_repo = job_repo

    def get_job(self, job_id: str) -> dict:
        job = self._job_repo.get(job_id)
        if job is None:
            raise JobNotFoundError()
        return job


job_service = JobService(job_repository)

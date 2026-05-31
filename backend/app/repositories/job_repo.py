from ..schemas.job import JobStatus


class JobRepository:
    """DB 대신 메모리 dict에 Job 상태를 저장하는 Mock Repository.

    서버 재시작 시 데이터는 초기화된다.
    나중에 RabbitMQ/Celery 기반 저장소(Redis 등)로 교체될 수 있다.
    """

    def __init__(self):
        self._jobs: dict = {}
        self._counter: int = 0

    def create(self, job_type: str) -> dict:
        self._counter += 1
        job_id = f"job_mock_{self._counter:03d}"
        job = {
            "jobId": job_id,
            "type": job_type,
            "status": JobStatus.pending.value,
            "progress": 0,
            "result": None,
            "error": None,
        }
        self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> dict | None:
        return self._jobs.get(job_id)

    def update_status(
        self, job_id: str, status: str, progress: int | None = None
    ) -> dict | None:
        job = self._jobs.get(job_id)
        if not job:
            return None
        job["status"] = status
        if progress is not None:
            job["progress"] = progress
        return job

    def complete(self, job_id: str, result: dict) -> dict | None:
        job = self._jobs.get(job_id)
        if not job:
            return None
        job["status"] = JobStatus.completed.value
        job["progress"] = 100
        job["result"] = result
        job["error"] = None
        return job

    def fail(self, job_id: str, error: str) -> dict | None:
        job = self._jobs.get(job_id)
        if not job:
            return None
        job["status"] = JobStatus.failed.value
        job["progress"] = 0
        job["result"] = None
        job["error"] = error
        return job


job_repository = JobRepository()

from collections.abc import Callable

from ..repositories.job_repo import job_repository
from ..schemas.job import JobStatus


class InMemoryJobManager:
    """Job 발급/상태 관리만 담당한다.

    도메인별 생성 로직(캐릭터/배경/TTS …)은 각 *_job_runner가 갖고,
    여기서는 "Job 생성 → running → 결과 콜백 실행 → completed/failed"만 처리한다.

    나중에 RabbitMQ/Celery로 교체할 때도 이 클래스만 publish 버전으로 바꾸면 된다.
    """

    def __init__(self, job_repo):
        self._job_repo = job_repo

    def run(
        self,
        job_type: str,
        build_result: Callable[[], dict],
        failed_detail: str,
        success_message: str,
    ) -> dict:
        """Job을 만들고 build_result()를 실행해 completed/failed 처리한다.

        build_result: Job 결과(dict)를 만드는 도메인 콜백. 예외가 나면 Job은 failed.
        반환: {jobId, status, message} (JobCreatedResponse 형태)
        """
        job = self._job_repo.create(job_type)
        job_id = job["jobId"]
        self._job_repo.update_status(job_id, JobStatus.running.value, progress=10)

        try:
            result = build_result()
            self._job_repo.complete(job_id, result=result)
        except Exception:  # noqa: BLE001
            self._job_repo.fail(job_id, failed_detail)
            return {
                "jobId": job_id,
                "status": JobStatus.failed.value,
                "message": failed_detail,
            }

        return {
            "jobId": job_id,
            "status": JobStatus.completed.value,
            "message": success_message,
        }


job_manager = InMemoryJobManager(job_repository)

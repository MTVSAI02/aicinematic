from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from ..repositories.job_repo import job_repository
from ..schemas.job import JobStatus


def _error_detail(exc: Exception, fallback: str) -> str:
    """실패 Job에 남길 에러 문자열. 실제 예외 메시지를 우선 보존한다.

    예: ComfyUIError("ComfyUI 실행 오류 [KSampler]: ...") → 그 메시지가 job.error에 남아
    "Character generation failed" 처럼 뭉개지지 않는다.
    """
    message = str(exc).strip()
    return message or fallback


class InMemoryJobManager:
    """Job 발급/상태 관리를 담당한다.

    도메인별 생성 로직(캐릭터/배경/TTS …)은 각 *_job_runner가 갖고,
    여기서는 "Job 생성 → running → 결과 콜백 실행 → completed/failed"만 처리한다.

    두 가지 실행 방식을 제공한다.
    - run()       : 동기. build_result()를 요청 안에서 즉시 실행해 completed/failed로 반환.
                    짧은 작업(예: 현재 TTS mock = 즉시 completed)에 사용한다.
    - run_async() : 비동기. jobId를 즉시 반환하고 build_result()는 백그라운드 스레드에서 실행.
                    오래 걸리는 작업(ComfyUI 이미지 생성, 보이스 클로닝, 렌더링)에 사용한다.

    ⚠️ MVP 한계: 비동기는 in-memory ThreadPoolExecutor로 처리한다.
       - 서버 재시작 시 pending/running Job은 유실된다(메모리 저장).
       - 단일 프로세스 기준이며, 배포 단계에서는 Redis Queue / Celery / RQ 등으로 교체한다.
       (이 클래스만 publish 버전으로 바꾸면 호출부는 그대로 둘 수 있다.)
    """

    def __init__(self, job_repo, max_workers: int = 4):
        self._job_repo = job_repo
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        # 동시성 보호는 job_repo가 내부 lock으로 직렬화한다(여기서 별도 lock 불필요).

    def run(
        self,
        job_type: str,
        build_result: Callable[[], dict],
        failed_detail: str,
        success_message: str,
    ) -> dict:
        """동기 실행. build_result()를 즉시 돌려 completed/failed로 반환한다.

        반환: {jobId, status(completed|failed), message} (JobCreatedResponse 형태)
        """
        job = self._job_repo.create(job_type)
        job_id = job["jobId"]
        self._job_repo.update_status(job_id, JobStatus.running.value, progress=10)

        try:
            result = build_result()
            self._job_repo.complete(job_id, result=result)
        except Exception as exc:  # noqa: BLE001
            detail = _error_detail(exc, failed_detail)
            self._job_repo.fail(job_id, detail)
            return {
                "jobId": job_id,
                "status": JobStatus.failed.value,
                "message": detail,
            }

        return {
            "jobId": job_id,
            "status": JobStatus.completed.value,
            "message": success_message,
        }

    def run_async(
        self,
        job_type: str,
        build_result: Callable[[], dict],
        failed_detail: str,
        accepted_message: str,
    ) -> dict:
        """비동기 실행. Job(pending)을 만들고 jobId를 즉시 반환한다.

        build_result()는 백그라운드 스레드에서 실행되며,
        프론트는 GET /api/jobs/{jobId} 로 pending→running→completed/failed 를 폴링한다.

        반환: {jobId, status="pending", message} (JobCreatedResponse 형태)
        """
        job = self._job_repo.create(job_type)  # status=pending
        job_id = job["jobId"]
        self._executor.submit(self._run_job, job_id, build_result, failed_detail)
        return {
            "jobId": job_id,
            "status": JobStatus.pending.value,
            "message": accepted_message,
        }

    def _run_job(
        self, job_id: str, build_result: Callable[[], dict], failed_detail: str
    ) -> None:
        """워커 스레드 본체: running 표시 → build_result 실행 → completed/failed."""
        self._job_repo.update_status(job_id, JobStatus.running.value, progress=10)
        try:
            result = build_result()
        except Exception as exc:  # noqa: BLE001
            self._job_repo.fail(job_id, _error_detail(exc, failed_detail))
            return
        self._job_repo.complete(job_id, result=result)


job_manager = InMemoryJobManager(job_repository)

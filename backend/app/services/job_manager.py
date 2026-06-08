from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from ..repositories.job_repo import job_repository
from ..schemas.job import JobStatus, JobType

# GPU / 외부 AI 서버에 직접 요청하는(또는 무거운) 작업.
# 단일 GPU 서버(클론/TTS, ComfyUI 이미지)는 동시 요청을 받으면 경합·과부하로 타임아웃/다운된다.
# → 이 유형들은 전용 직렬 큐(동시성 1)로 "큐에 쌓아 하나씩" 처리한다. (경량 작업은 일반 풀에서 병렬)
_SERIAL_JOB_TYPES = frozenset({
    JobType.voice_clone.value,
    JobType.tts_generate.value,
    JobType.tts_story_generate.value,
    JobType.character_generate.value,
    JobType.character_pose_generate.value,
    JobType.background_generate.value,
    JobType.render_generate.value,
})


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
        # 경량/일반 작업용 풀(병렬 허용).
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        # GPU·외부 AI 작업 전용 직렬 큐(동시성 1) — 단일 GPU 서버에 동시 요청이 가지 않게 하나씩 처리.
        self._gpu_executor = ThreadPoolExecutor(max_workers=1)
        # 동시성 보호는 job_repo가 내부 lock으로 직렬화한다(여기서 별도 lock 불필요).

    def _executor_for(self, job_type: str | None):
        """GPU/외부 AI 작업이면 직렬 큐, 아니면 일반 풀을 고른다."""
        return self._gpu_executor if job_type in _SERIAL_JOB_TYPES else self._executor

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
            self._notify_job_done(job_id)
            return {
                "jobId": job_id,
                "status": JobStatus.failed.value,
                "message": detail,
            }

        self._notify_job_done(job_id)
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
        payload: dict | None = None,
    ) -> dict:
        """비동기 실행. Job(pending)을 만들고 jobId를 즉시 반환한다.

        build_result()는 백그라운드 스레드에서 실행되며,
        프론트는 GET /api/jobs/{jobId} 로 pending→running→completed/failed 를 폴링한다.

        반환: {jobId, status="pending", message} (JobCreatedResponse 형태)
        """
        job = self._job_repo.create(job_type, payload=payload)  # status=pending
        job_id = job["jobId"]
        # GPU/외부 AI 작업은 직렬 큐로 → 동시 요청이 단일 GPU 를 때리지 않게 하나씩 처리.
        self._executor_for(job_type).submit(self._run_job, job_id, build_result, failed_detail)
        return {
            "jobId": job_id,
            "status": JobStatus.pending.value,
            "message": accepted_message,
        }

    def resume_async(
        self,
        job_id: str,
        build_result: Callable[[], dict],
        failed_detail: str,
        job_type: str | None = None,
    ) -> None:
        """Resume an already persisted pending/running job with the same jobId.

        job_type 을 주면 그 유형 기준으로 풀을 고른다(미지정이면 GPU 직렬 큐 — 재개 대상은 보통 GPU 작업).
        """
        executor = self._executor_for(job_type) if job_type else self._gpu_executor
        executor.submit(self._run_job, job_id, build_result, failed_detail)

    def _notify_job_done(self, job_id: str) -> None:
        """job 완료/실패 직후 알림 생성(대상 job 만 — notification_service 가 필터).

        알림 생성이 job 처리를 깨면 안 되므로 실패는 전부 무시. lazy import 로 순환 방지.
        """
        try:
            from .notification_service import notification_service

            notification_service.create_for_job(self._job_repo.get(job_id))
        except Exception:  # noqa: BLE001
            pass

    def _run_job(
        self, job_id: str, build_result: Callable[[], dict], failed_detail: str
    ) -> None:
        """워커 스레드 본체: running 표시 → build_result 실행 → completed/failed → 알림."""
        self._job_repo.update_status(job_id, JobStatus.running.value, progress=10)
        try:
            result = build_result()
        except Exception as exc:  # noqa: BLE001
            self._job_repo.fail(job_id, _error_detail(exc, failed_detail))
            self._notify_job_done(job_id)
            return
        self._job_repo.complete(job_id, result=result)
        self._notify_job_done(job_id)


job_manager = InMemoryJobManager(job_repository)

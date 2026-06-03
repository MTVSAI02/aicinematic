"""Job 상태 repository (PostgreSQL).

비동기 작업(캐릭터/배경/TTS/클론/렌더)의 상태를 PG `jobs` 테이블에 저장한다.
- 기존 in-memory / SQLite 구현과 같은 메서드/반환(dict, camelCase)을 유지한다.
- job_id = prefix+ULID(job_…) → 카운터 충돌 없음(다중 프로세스에서도 안전).
- 서버 재시작 후에도 상태가 남아 list_unfinished 로 미완료 작업을 복구할 수 있다.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from ..core.ids import new_id
from ..db.models import Job
from ..db.session import SessionLocal
from ..schemas.job import JobStatus


def _iso(dt: datetime | None):
    return dt.isoformat() if dt else None


def _to_dict(job: Job) -> dict:
    return {
        "jobId": job.id,
        "type": job.type,
        "storyId": job.story_id,
        "status": job.status,
        "progress": job.progress,
        "result": job.result,
        "error": job.error,
        "payload": job.payload,
        "createdAt": _iso(job.created_at),
        "updatedAt": _iso(job.updated_at),
    }


class JobRepository:
    """PG 기반 Job 저장소. 동시성은 DB가 처리(요청/워커 스레드별 SessionLocal)."""

    def create(self, job_type: str, payload: dict | None = None) -> dict:
        with SessionLocal() as db:
            job = Job(
                id=new_id("job"),
                type=job_type,
                story_id=(payload or {}).get("storyId"),
                status=JobStatus.pending.value,
                progress=0,
                payload=payload,
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            return _to_dict(job)

    def get(self, job_id: str) -> dict | None:
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            return _to_dict(job) if job else None

    def update_status(self, job_id: str, status: str, progress: int | None = None) -> dict | None:
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            if job is None:
                return None
            job.status = status
            if progress is not None:
                job.progress = progress
            db.commit()
            db.refresh(job)
            return _to_dict(job)

    def complete(self, job_id: str, result: dict) -> dict | None:
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            if job is None:
                return None
            job.status = JobStatus.completed.value
            job.progress = 100
            job.result = result
            job.error = None
            db.commit()
            db.refresh(job)
            return _to_dict(job)

    def fail(self, job_id: str, error: str) -> dict | None:
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            if job is None:
                return None
            job.status = JobStatus.failed.value
            job.progress = 0
            job.result = None
            job.error = error
            db.commit()
            db.refresh(job)
            return _to_dict(job)

    def list_unfinished(self, job_type: str | None = None) -> list[dict]:
        with SessionLocal() as db:
            stmt = select(Job).where(
                Job.status.in_([JobStatus.pending.value, JobStatus.running.value])
            )
            if job_type:
                stmt = stmt.where(Job.type == job_type)
            stmt = stmt.order_by(Job.created_at)
            return [_to_dict(j) for j in db.execute(stmt).scalars().all()]


job_repository = JobRepository()

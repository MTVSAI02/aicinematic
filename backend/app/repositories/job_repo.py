import json
import sqlite3
import threading
from datetime import datetime, timezone

from ..core.config import STORAGE_ROOT
from ..schemas.job import JobStatus


class JobRepository:
    """DB 대신 메모리 dict에 Job 상태를 저장하는 Mock Repository.

    서버 재시작 시 데이터는 초기화된다.
    비동기 Job(워커 스레드)에서 동시에 생성/갱신될 수 있어 lock으로 보호한다.
    나중에 RabbitMQ/Celery 기반 저장소(Redis 등)로 교체될 수 있다.
    """

    def __init__(self):
        STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
        self._db_path = STORAGE_ROOT / "jobs.sqlite3"
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()
        self._counter = self._load_counter()

    def _init_db(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    story_id TEXT,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL,
                    result_json TEXT,
                    error TEXT,
                    payload_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def _load_counter(self) -> int:
        rows = self._conn.execute("SELECT job_id FROM jobs").fetchall()
        max_seen = 0
        for row in rows:
            job_id = row["job_id"]
            if not isinstance(job_id, str) or not job_id.startswith("job_mock_"):
                continue
            try:
                max_seen = max(max_seen, int(job_id.rsplit("_", 1)[1]))
            except ValueError:
                continue
        return max_seen

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _to_json(value: dict | None) -> str | None:
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _from_json(value: str | None) -> dict | None:
        if not value:
            return None
        return json.loads(value)

    def _row_to_job(self, row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        return {
            "jobId": row["job_id"],
            "type": row["type"],
            "storyId": row["story_id"],
            "status": row["status"],
            "progress": row["progress"],
            "result": self._from_json(row["result_json"]),
            "error": row["error"],
            "payload": self._from_json(row["payload_json"]),
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def create(self, job_type: str, payload: dict | None = None) -> dict:
        with self._lock:
            self._counter += 1
            job_id = f"job_mock_{self._counter:03d}"
            now = self._now()
            story_id = (payload or {}).get("storyId")
            job = {
                "jobId": job_id,
                "type": job_type,
                "storyId": story_id,
                "status": JobStatus.pending.value,
                "progress": 0,
                "result": None,
                "error": None,
                "payload": payload,
                "createdAt": now,
                "updatedAt": now,
            }
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO jobs (
                        job_id, type, story_id, status, progress, result_json,
                        error, payload_json, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job_id,
                        job_type,
                        story_id,
                        JobStatus.pending.value,
                        0,
                        None,
                        None,
                        self._to_json(payload),
                        now,
                        now,
                    ),
                )
            return job

    def get(self, job_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            return self._row_to_job(row)

    def update_status(
        self, job_id: str, status: str, progress: int | None = None
    ) -> dict | None:
        with self._lock:
            job = self.get(job_id)
            if job is None:
                return None
            next_progress = progress if progress is not None else job["progress"]
            now = self._now()
            with self._conn:
                self._conn.execute(
                    """
                    UPDATE jobs
                    SET status = ?, progress = ?, updated_at = ?
                    WHERE job_id = ?
                    """,
                    (status, next_progress, now, job_id),
                )
            job["status"] = status
            job["progress"] = next_progress
            job["updatedAt"] = now
            return job

    def complete(self, job_id: str, result: dict) -> dict | None:
        with self._lock:
            job = self.get(job_id)
            if job is None:
                return None
            now = self._now()
            with self._conn:
                self._conn.execute(
                    """
                    UPDATE jobs
                    SET status = ?, progress = ?, result_json = ?, error = ?, updated_at = ?
                    WHERE job_id = ?
                    """,
                    (
                        JobStatus.completed.value,
                        100,
                        self._to_json(result),
                        None,
                        now,
                        job_id,
                    ),
                )
            job["status"] = JobStatus.completed.value
            job["progress"] = 100
            job["result"] = result
            job["error"] = None
            job["updatedAt"] = now
            return job

    def fail(self, job_id: str, error: str) -> dict | None:
        with self._lock:
            job = self.get(job_id)
            if job is None:
                return None
            now = self._now()
            with self._conn:
                self._conn.execute(
                    """
                    UPDATE jobs
                    SET status = ?, progress = ?, result_json = ?, error = ?, updated_at = ?
                    WHERE job_id = ?
                    """,
                    (JobStatus.failed.value, 0, None, error, now, job_id),
                )
            job["status"] = JobStatus.failed.value
            job["progress"] = 0
            job["result"] = None
            job["error"] = error
            job["updatedAt"] = now
            return job

    def list_unfinished(self, job_type: str | None = None) -> list[dict]:
        with self._lock:
            sql = """
                SELECT * FROM jobs
                WHERE status IN (?, ?)
            """
            params: list = [JobStatus.pending.value, JobStatus.running.value]
            if job_type:
                sql += " AND type = ?"
                params.append(job_type)
            sql += " ORDER BY created_at ASC"
            rows = self._conn.execute(sql, params).fetchall()
            return [self._row_to_job(row) for row in rows]


job_repository = JobRepository()

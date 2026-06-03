import json
import sqlite3
import threading
from datetime import datetime, timezone

from ..core.config import STORAGE_ROOT


class InMemoryTTSAudioRepository:
    """TTS audio 결과를 저장하는 메모리 Repository.

    mock 단계에서는 audioUrl=None 메타데이터만 보관하고,
    AI/TTS 연동 시 audioId 기준으로 audioUrl/durationSec/error를 갱신한다.
    서버 재시작 시 데이터는 초기화된다.
    """

    def __init__(self):
        self._audios: dict = {}
        self._counter: int = 0

    def create_many(self, audios: list[dict]) -> list[dict]:
        """audio 목록을 저장하면서 audioId를 발급한다. 저장된(=audioId 포함) 목록을 반환한다."""
        saved = []
        for audio in audios:
            self._counter += 1
            audio_id = f"audio_mock_{self._counter:03d}"
            record = {**audio, "audioId": audio_id}
            self._audios[audio_id] = record
            saved.append(record)
        return saved

    def list_by_scene(self, story_id: str, scene_id: str) -> list[dict]:
        return [
            a
            for a in self._audios.values()
            if a.get("storyId") == story_id and a.get("sceneId") == scene_id
        ]

    def get(self, audio_id: str) -> dict | None:
        return self._audios.get(audio_id)

    def apply_ai_result(self, audios: list[dict]) -> list[dict]:
        """AI/TTS 응답을 audioId 기준으로 저장 레코드에 반영한다."""
        updated = []
        for audio in audios:
            audio_id = audio.get("audioId")
            if not audio_id or audio_id not in self._audios:
                continue

            record = self._audios[audio_id]
            record["audioUrl"] = audio.get("audioUrl")
            record["durationSec"] = audio.get("durationSec")
            record["error"] = audio.get("error")
            updated.append(record)
        return updated

    def delete(self, audio_id: str) -> bool:
        if audio_id in self._audios:
            del self._audios[audio_id]
            return True
        return False

    def delete_by_scene(self, story_id: str, scene_id: str) -> int:
        """특정 story+scene의 기존 audio를 모두 삭제하고 삭제 개수를 반환한다. (재생성 교체용)"""
        targets = [a["audioId"] for a in self.list_by_scene(story_id, scene_id)]
        for audio_id in targets:
            del self._audios[audio_id]
        return len(targets)


class SQLiteTTSAudioRepository:
    """Persist TTS audio records to storage/tts_audios.sqlite3."""

    def __init__(self):
        STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
        self._db_path = STORAGE_ROOT / "tts_audios.sqlite3"
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()
        self._counter = self._load_counter()

    def _init_db(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tts_audios (
                    audio_id TEXT PRIMARY KEY,
                    story_id TEXT NOT NULL,
                    scene_id TEXT NOT NULL,
                    item_index INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    speaker TEXT,
                    audio_url TEXT,
                    duration_sec REAL,
                    error TEXT,
                    record_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_tts_audios_scene
                ON tts_audios(story_id, scene_id, item_index)
                """
            )

    def _load_counter(self) -> int:
        rows = self._conn.execute("SELECT audio_id FROM tts_audios").fetchall()
        max_seen = 0
        for row in rows:
            audio_id = row["audio_id"]
            if not isinstance(audio_id, str) or not audio_id.startswith("audio_mock_"):
                continue
            try:
                max_seen = max(max_seen, int(audio_id.rsplit("_", 1)[1]))
            except ValueError:
                continue
        return max_seen

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _to_json(record: dict) -> str:
        return json.dumps(record, ensure_ascii=False)

    @staticmethod
    def _from_json(value: str) -> dict:
        return json.loads(value)

    def _next_audio_id(self) -> str:
        self._counter += 1
        return f"audio_mock_{self._counter:03d}"

    def _row_to_audio(self, row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        record = self._from_json(row["record_json"])
        record.update(
            {
                "audioId": row["audio_id"],
                "storyId": row["story_id"],
                "sceneId": row["scene_id"],
                "itemIndex": row["item_index"],
                "text": row["text"],
                "speaker": row["speaker"],
                "audioUrl": row["audio_url"],
                "durationSec": row["duration_sec"],
                "error": row["error"],
            }
        )
        return record

    def _save_record(self, record: dict) -> dict:
        now = self._now()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO tts_audios (
                    audio_id, story_id, scene_id, item_index, text, speaker,
                    audio_url, duration_sec, error, record_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(audio_id) DO UPDATE SET
                    story_id = excluded.story_id,
                    scene_id = excluded.scene_id,
                    item_index = excluded.item_index,
                    text = excluded.text,
                    speaker = excluded.speaker,
                    audio_url = excluded.audio_url,
                    duration_sec = excluded.duration_sec,
                    error = excluded.error,
                    record_json = excluded.record_json,
                    updated_at = excluded.updated_at
                """,
                (
                    record["audioId"],
                    record["storyId"],
                    record["sceneId"],
                    record["itemIndex"],
                    record.get("text") or "",
                    record.get("speaker"),
                    record.get("audioUrl"),
                    record.get("durationSec"),
                    record.get("error"),
                    self._to_json(record),
                    now,
                    now,
                ),
            )
        return record

    def create_many(self, audios: list[dict]) -> list[dict]:
        saved = []
        with self._lock:
            for audio in audios:
                record = {**audio, "audioId": self._next_audio_id()}
                saved.append(self._save_record(record))
        return saved

    def upsert_target(self, audio: dict, audio_id: str | None = None) -> dict:
        with self._lock:
            record = {**audio, "audioId": audio_id or self._next_audio_id()}
            return self._save_record(record)

    def list_by_scene(self, story_id: str, scene_id: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT * FROM tts_audios
                WHERE story_id = ? AND scene_id = ?
                ORDER BY item_index ASC
                """,
                (story_id, scene_id),
            ).fetchall()
            by_item = {}
            for row in rows:
                audio = self._row_to_audio(row)
                item_index = audio.get("itemIndex")
                current = by_item.get(item_index)
                if current is None or (audio.get("audioUrl") and not current.get("audioUrl")):
                    by_item[item_index] = audio
            return [by_item[key] for key in sorted(by_item)]

    def get(self, audio_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM tts_audios WHERE audio_id = ?",
                (audio_id,),
            ).fetchone()
            return self._row_to_audio(row)

    def apply_ai_result(self, audios: list[dict]) -> list[dict]:
        updated = []
        with self._lock:
            for audio in audios:
                audio_id = audio.get("audioId")
                if not audio_id:
                    continue
                record = self.get(audio_id)
                if record is None:
                    continue
                record["audioUrl"] = audio.get("audioUrl")
                record["durationSec"] = audio.get("durationSec")
                record["error"] = audio.get("error")
                updated.append(self._save_record(record))
        return updated

    def delete(self, audio_id: str) -> bool:
        with self._lock:
            with self._conn:
                cursor = self._conn.execute(
                    "DELETE FROM tts_audios WHERE audio_id = ?",
                    (audio_id,),
                )
            return cursor.rowcount > 0

    def delete_by_scene(self, story_id: str, scene_id: str) -> int:
        with self._lock:
            with self._conn:
                cursor = self._conn.execute(
                    "DELETE FROM tts_audios WHERE story_id = ? AND scene_id = ?",
                    (story_id, scene_id),
                )
            return cursor.rowcount


tts_audio_repository = SQLiteTTSAudioRepository()

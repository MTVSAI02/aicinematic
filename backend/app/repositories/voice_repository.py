"""보이스 라이브러리 repository (PostgreSQL).

기존 in-memory 와 같은 메서드/반환(dict, camelCase 키)을 유지해 서비스/스키마는 그대로 쓴다.
ID = prefix+ULID (preset 은 시스템 고정 ID). 파일은 storage, DB엔 path/url만.
preset 4개는 Alembic 0002 가 시드하지만, seed_default_narrator_voices() 로도 idempotent 보장 + 샘플 경로 갱신.
"""

from datetime import datetime

from sqlalchemy import select

from ..core.config import VOICE_STORAGE_DIR, storage_url
from ..core.ids import new_id
from ..db.models import Voice
from ..db.session import SessionLocal

DEFAULT_NARRATOR_VOICE_PRESETS: list[dict] = [
    {"voiceId": "voice_preset_narrator_calm_001", "name": "차분한 나레이션",
     "description": "잔잔하고 따뜻하게 동화를 읽어주는 목소리",
     "voicePrompt": "calm, warm, gentle narrator voice for fairy tale storytelling"},
    {"voiceId": "voice_preset_narrator_bright_001", "name": "밝은 나레이션",
     "description": "밝고 친근하게 이야기를 읽어주는 목소리",
     "voicePrompt": "bright, friendly, cheerful narrator voice for children story"},
    {"voiceId": "voice_preset_narrator_soft_001", "name": "부드러운 나레이션",
     "description": "포근하고 부드러운 분위기의 동화 구연 목소리",
     "voicePrompt": "soft, cozy, gentle storytelling voice"},
    {"voiceId": "voice_preset_narrator_serious_001", "name": "진지한 나레이션",
     "description": "안정감 있고 차분하게 장면을 설명하는 목소리",
     "voicePrompt": "serious, calm, stable narrator voice"},
]

_CLONE_UPDATE_FIELDS = frozenset(
    {"status", "sampleAudioUrl", "provider", "model", "error", "referenceAudioUrl", "referenceText", "updatedAt"}
)
# camelCase(서비스/스키마) ↔ snake(DB 컬럼)
_CAMEL_TO_COL = {
    "name": "name", "description": "description", "voicePrompt": "voice_prompt",
    "voiceType": "voice_type", "isPreset": "is_preset", "speakerLabel": "speaker_label",
    "characterId": "character_id", "referenceAudioUrl": "reference_audio_url",
    "referenceText": "reference_text", "sampleAudioUrl": "sample_audio_url",
    "provider": "provider", "model": "model", "status": "status", "error": "error",
}


def _iso(dt: datetime | None):
    return dt.isoformat() if dt else None


def _to_dict(v: Voice) -> dict:
    return {
        "voiceId": v.id,
        "name": v.name,
        "description": v.description,
        "voicePrompt": v.voice_prompt,
        "voiceType": v.voice_type,
        "isPreset": v.is_preset,
        "speakerLabel": v.speaker_label,
        "characterId": v.character_id,
        "referenceAudioUrl": v.reference_audio_url,
        "referenceText": v.reference_text,
        "sampleAudioUrl": v.sample_audio_url,
        "provider": v.provider,
        "model": v.model,
        "status": v.status,
        "error": v.error,
        "createdAt": _iso(v.created_at),
        "updatedAt": _iso(v.updated_at),
    }


class VoiceRepository:
    @staticmethod
    def _preset_sample_url(voice_id: str) -> str | None:
        if (VOICE_STORAGE_DIR / voice_id / "sample.wav").exists():
            return storage_url("voices", voice_id, "sample.wav")
        return None

    def seed_default_narrator_voices(self) -> None:
        """preset 4개 보장(idempotent) + sample.wav 존재 시 sampleAudioUrl 갱신."""
        with SessionLocal() as db:
            for preset in DEFAULT_NARRATOR_VOICE_PRESETS:
                vid = preset["voiceId"]
                sample_url = self._preset_sample_url(vid)
                row = db.get(Voice, vid)
                if row is None:
                    db.add(Voice(
                        id=vid, name=preset["name"], description=preset["description"],
                        voice_prompt=preset["voicePrompt"], voice_type="narrator",
                        is_preset=True, status="ready", sample_audio_url=sample_url,
                    ))
                else:
                    row.sample_audio_url = sample_url
            db.commit()

    def save(self, voice_data: dict) -> dict:
        with SessionLocal() as db:
            v = Voice(
                id=new_id("voice"),
                name=voice_data.get("name"),
                description=voice_data.get("description"),
                voice_prompt=voice_data.get("voicePrompt"),
                voice_type=voice_data.get("voiceType") or "character",
                is_preset=False,
                speaker_label=voice_data.get("speakerLabel"),
                character_id=voice_data.get("characterId"),
                reference_audio_url=voice_data.get("referenceAudioUrl"),
                reference_text=voice_data.get("referenceText"),
                sample_audio_url=voice_data.get("sampleAudioUrl"),
                provider=voice_data.get("provider"),
                model=voice_data.get("model"),
                status=voice_data.get("status") or "pending",
                error=voice_data.get("error"),
            )
            db.add(v)
            db.commit()
            db.refresh(v)
            return _to_dict(v)

    def apply_clone_update(self, voice_id: str, data: dict) -> dict | None:
        with SessionLocal() as db:
            v = db.get(Voice, voice_id)
            if not v:
                return None
            for key, value in data.items():
                if key in _CLONE_UPDATE_FIELDS and key != "updatedAt":
                    setattr(v, _CAMEL_TO_COL[key], value)
            db.commit()
            db.refresh(v)
            return _to_dict(v)

    def list(self) -> list[dict]:
        with SessionLocal() as db:
            rows = db.execute(select(Voice).order_by(Voice.created_at)).scalars().all()
            return [_to_dict(v) for v in rows]

    def get(self, voice_id: str) -> dict | None:
        with SessionLocal() as db:
            v = db.get(Voice, voice_id)
            return _to_dict(v) if v else None

    def update(self, voice_id: str, update_data: dict) -> dict | None:
        with SessionLocal() as db:
            v = db.get(Voice, voice_id)
            if not v:
                return None
            for field in ("description", "voicePrompt"):
                if field in update_data:
                    setattr(v, _CAMEL_TO_COL[field], update_data[field])
            if update_data.get("name") is not None:
                v.name = update_data["name"]
            db.commit()
            db.refresh(v)
            return _to_dict(v)

    def delete(self, voice_id: str) -> bool:
        with SessionLocal() as db:
            v = db.get(Voice, voice_id)
            if not v:
                return False
            db.delete(v)
            db.commit()
            return True


voice_repository = VoiceRepository()

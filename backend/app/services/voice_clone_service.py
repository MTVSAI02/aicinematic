"""보이스 클로닝 orchestration.

흐름: 검증 → voice record(pending) 생성 → reference 오디오 저장
     → voice_clone Job(async): processing → AI 클론 요청(multipart) → sample.wav 저장 → ready / 실패 시 failed.
- voice.status 는 Job status 와 별개로 직접 관리한다(processing/ready/failed + error). 결과는 PostgreSQL 영속.
- ⚠️ 캐릭터/나레이션 연결은 여기서 하지 않는다 — /voice 페이지의 명시적 연결 API(ready voice만)만 담당.
  (characterId 는 "어떤 캐릭터용으로 만들었나" 메타로만 저장하고, 실제 연결은 안 함)
- 내부 절대경로는 AI/백엔드 사이에서만 — 응답/저장 노출은 /storage URL 만.
"""

from datetime import datetime, timezone

from ..core.config import VOICE_STORAGE_DIR, storage_url
from ..core.exceptions import (
    CharacterNotFoundError,
    InvalidAudioFileError,
    VoiceCloneFailedError,
    VoiceCloneValidationError,
)
from ..repositories.character_repo import character_repository
from ..repositories.voice_repository import voice_repository
from ..schemas.job import JobType
from .ai_voice_client import clone_voice as ai_clone_voice
from .job_manager import job_manager

_ALLOWED_EXT = {"webm", "wav", "mp3", "m4a"}
_ALLOWED_MIME = {
    "audio/webm", "audio/wav", "audio/x-wav", "audio/wave",
    "audio/mpeg", "audio/mp3", "audio/mp4", "audio/x-m4a", "audio/aac", "audio/ogg",
}
_MAX_AUDIO_BYTES = 20 * 1024 * 1024  # 20MB — 20초 음성 MVP엔 충분(과대 업로드 차단)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ext_of(filename: str | None) -> str | None:
    if not filename or "." not in filename:
        return None
    return filename.rsplit(".", 1)[1].lower()


def create_voice_clone_job(
    *,
    name: str,
    voice_type: str,
    reference_text: str,
    voice_prompt: str | None,
    character_id: str | None,
    speaker_label: str | None,
    audio_bytes: bytes,
    audio_filename: str | None,
    content_type: str | None = None,
) -> dict:
    # ── 검증 ──
    if voice_type not in ("narrator", "character"):
        raise VoiceCloneValidationError("voiceType must be 'narrator' or 'character'.")
    if not (name or "").strip():
        raise VoiceCloneValidationError("name must not be blank.")
    if not (reference_text or "").strip():
        raise VoiceCloneValidationError("referenceText must not be blank.")
    if not audio_bytes:
        raise InvalidAudioFileError("audioFile is empty.")
    if len(audio_bytes) > _MAX_AUDIO_BYTES:
        raise InvalidAudioFileError(f"audioFile too large (max {_MAX_AUDIO_BYTES // (1024 * 1024)}MB).")
    ext = _ext_of(audio_filename)
    if ext not in _ALLOWED_EXT:
        raise InvalidAudioFileError()
    # MIME 검증: content_type 이 주어졌고 허용 목록 밖이면 거부 (빈/octet-stream 은 ext 검증으로 대체)
    ctype = (content_type or "").split(";")[0].strip().lower()
    if ctype and ctype not in _ALLOWED_MIME and ctype != "application/octet-stream":
        raise InvalidAudioFileError(f"unsupported audio MIME: {ctype}")
    # narrator 는 characterId 없음. character 면 있을 때만 존재 검증(연결은 안 함 — 메타로만 저장).
    char_id = character_id if (voice_type == "character" and character_id) else None
    if char_id and character_repository.get(char_id) is None:
        raise CharacterNotFoundError()

    # ── voice record(pending) 생성 ──
    now = _now()
    voice = voice_repository.save(
        {
            "name": name.strip(),
            "voiceType": voice_type,
            "speakerLabel": (speaker_label or "").strip() or None,
            "characterId": char_id,
            "voicePrompt": voice_prompt,
            "referenceText": reference_text.strip(),
            "status": "pending",
            "createdAt": now,
            "updatedAt": now,
        }
    )
    voice_id = voice["voiceId"]

    # ── reference 오디오 저장 ──
    vdir = VOICE_STORAGE_DIR / voice_id
    vdir.mkdir(parents=True, exist_ok=True)
    (vdir / f"reference.{ext}").write_bytes(audio_bytes)
    reference_url = storage_url("voices", voice_id, f"reference.{ext}")
    voice_repository.apply_clone_update(voice_id, {"referenceAudioUrl": reference_url})

    # ⚠️ 캐릭터 자동 연결 안 함 (확정 설계: 연결은 /voice 에서 ready voice 만).
    #    characterId 는 voice 레코드에 메타로만 저장됨.

    # ── voice_clone Job (비동기) ──
    def build_result() -> dict:
        voice_repository.apply_clone_update(voice_id, {"status": "processing", "updatedAt": _now()})
        try:
            res = ai_clone_voice(
                voice_id=voice_id,
                voice_type=voice_type,
                character_id=char_id,
                reference_text=reference_text.strip(),
                voice_prompt=voice_prompt,
                audio_bytes=audio_bytes,
                audio_ext=ext,
            )
            (vdir / "sample.wav").write_bytes(res["sample_bytes"])
            sample_url = storage_url("voices", voice_id, "sample.wav")
            voice_repository.apply_clone_update(
                voice_id,
                {
                    "status": "ready",
                    "sampleAudioUrl": sample_url,
                    "provider": res.get("provider"),
                    "model": res.get("model"),
                    "error": None,
                    "updatedAt": _now(),
                },
            )
            return {"voiceId": voice_id, "status": "ready", "sampleAudioUrl": sample_url}
        except Exception as e:  # noqa: BLE001  (voice.status=failed 로 남기고 Job 도 실패시킴)
            voice_repository.apply_clone_update(
                voice_id, {"status": "failed", "error": str(e), "updatedAt": _now()}
            )
            raise

    resp = job_manager.run_async(
        JobType.voice_clone.value,
        build_result,
        VoiceCloneFailedError.detail,
        "Voice cloning job started.",
    )
    resp["voiceId"] = voice_id  # 응답에 voiceId 포함(폴링 전에도 어떤 보이스인지 알 수 있게)
    return resp

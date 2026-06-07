"""기본 나레이션 preset 보이스 seed (앱 시작 시 idempotent 보장).

Qwen3-TTS CustomVoice 내장 화자 4종을 우리 voiceId 로 노출한다.
(voiceId → Qwen speaker 매핑은 AI 서버가 소유 — calm=sohee/bright=serena/soft=vivian/serious=ryan)

- **DB 초기화/팀원 환경에서도 항상 나레이션 선택이 가능하도록** startup 마다 upsert.
- preset 은 **모델 내장 목소리**라 reference 불필요(referenceAudioUrl/Text = null).
- 미리듣기 sample: repo 동봉 자산(`app/seed_assets/preset_voices/{voiceId}.wav`)이 있으면
  storage(`/storage/voices/{voiceId}/sample.wav`)로 복사하고 sampleAudioUrl 을 채운다.
  자산이 없으면 sampleAudioUrl=null(미리듣기 비활성) — TTS 합성 자체에는 영향 없음.
  (자산은 AI 서버로 1회 생성 후 동봉한다 — `scripts`/직접 생성)
"""

import logging
import shutil
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert as pg_insert

from ..core.config import VOICE_STORAGE_DIR, storage_url
from ..db.models import Voice
from ..db.session import SessionLocal

logger = logging.getLogger(__name__)

# repo 동봉 미리듣기 자산 폴더 (storage 는 gitignore 라 여기 두고 startup 에 storage 로 복사)
_SEED_ASSET_DIR = Path(__file__).resolve().parent.parent / "seed_assets" / "preset_voices"

_PROVIDER = "qwen"
_MODEL = "Qwen3-TTS-12Hz-0.6B-CustomVoice"

# 기본 나레이션 4종 (고정 voiceId — AI 서버 QWEN_SPEAKER_BY_VOICE_ID 매핑과 일치해야 함)
PRESET_NARRATOR_VOICES = [
    {"id": "voice_preset_narrator_calm_001", "name": "차분한 나레이션", "voice_prompt": "calm, warm, gentle narrator voice"},
    {"id": "voice_preset_narrator_bright_001", "name": "밝은 나레이션", "voice_prompt": "bright, friendly, cheerful narrator voice"},
    {"id": "voice_preset_narrator_soft_001", "name": "부드러운 나레이션", "voice_prompt": "soft, cozy, gentle storytelling voice"},
    {"id": "voice_preset_narrator_serious_001", "name": "진지한 나레이션", "voice_prompt": "serious, calm, stable narrator voice"},
]


def _ensure_sample(voice_id: str) -> str | None:
    """동봉 자산이 있으면 storage 로 복사하고 sampleAudioUrl 반환. 없으면 None."""
    asset = _SEED_ASSET_DIR / f"{voice_id}.wav"
    if not asset.is_file():
        return None
    vdir = VOICE_STORAGE_DIR / voice_id
    vdir.mkdir(parents=True, exist_ok=True)
    dest = vdir / "sample.wav"
    if not dest.exists():
        shutil.copyfile(asset, dest)
    return storage_url("voices", voice_id, "sample.wav")


def seed_preset_narrator_voices() -> None:
    """기본 나레이션 4종을 upsert(self-healing). 실패해도 앱 기동을 막지 않는다."""
    try:
        with SessionLocal() as db:
            for p in PRESET_NARRATOR_VOICES:
                sample_url = _ensure_sample(p["id"])
                values = {
                    "id": p["id"],
                    "name": p["name"],
                    "voice_type": "narrator",
                    "is_preset": True,
                    "status": "ready",
                    "voice_prompt": p["voice_prompt"],
                    "provider": _PROVIDER,
                    "model": _MODEL,
                    "sample_audio_url": sample_url,
                }
                stmt = pg_insert(Voice).values(**values).on_conflict_do_update(
                    index_elements=[Voice.id],
                    # 시스템 소유 preset — 표준값으로 self-heal(이름/상태/샘플 갱신)
                    set_={
                        "name": values["name"],
                        "voice_type": values["voice_type"],
                        "is_preset": True,
                        "status": "ready",
                        "voice_prompt": values["voice_prompt"],
                        "provider": _PROVIDER,
                        "model": _MODEL,
                        "sample_audio_url": sample_url,
                    },
                )
                db.execute(stmt)
            db.commit()
        logger.info("기본 나레이션 preset 보이스 %d종 seed 완료", len(PRESET_NARRATOR_VOICES))
    except Exception as exc:  # noqa: BLE001 — seed 실패가 앱 기동을 막지 않게
        logger.warning("preset 나레이션 보이스 seed 실패: %s", exc)

"""대상별(나레이션/캐릭터) 보이스 잠금 + 대상별 TTS 생성 orchestration.

흐름(/voice):
  대상별 lock → 검증(voiceId 연결 + ready) → 그 대상 lockStatus=locked / ttsStatus=generating
              → 그 대상 item만 백그라운드 TTS 생성 → ttsStatus=ready/failed
  대상별 unlock → lockStatus=unlocked, ttsStatus=stale (보이스 변경 가능)
  모든 필수 대상(나레이션 + 등장 캐릭터 전부)이 locked 여야 nextStepEnabled=true ([배경 →] 활성).

필수 대상:
  - narration item 이 있으면 "나레이션"
  - dialogue speaker 와 매칭되는 모든 캐릭터
  - speaker 인데 매칭 캐릭터가 없으면 matched=False → 잠글 수 없음 → nextStep 막힘(캐릭터 먼저 생성).

대상별 audio 만 교체하므로(다른 대상 audio 유지) 캐릭터 하나만 다시 잠가도 나머지는 보존된다.
"""

from ..core.exceptions import (
    StoryNotFoundError,
    VoiceLockTargetNotFoundError,
    VoiceNotConnectedError,
    VoiceNotReadyError,
)
from ..repositories.character_repo import character_repository
from ..repositories.story_repo import story_repository
from ..repositories.voice_repository import voice_repository
from ..schemas.job import JobType
from .image_resolve import resolve_character_display_image
from .job_manager import job_manager
from .tts_service import tts_service

NARRATION_TARGET_ID = "narration"


def _voice_name(voice_id: str | None) -> str | None:
    if not voice_id:
        return None
    voice = voice_repository.get(voice_id)
    return voice.get("name") if voice else None


def _voice_ready(voice_id: str | None) -> bool:
    if not voice_id:
        return False
    voice = voice_repository.get(voice_id)
    return bool(voice and voice.get("status") == "ready")


def _collect_targets(story: dict) -> list[dict]:
    """필수 대상 목록(순서 유지). 각 대상의 매칭/연결 정보 포함(lockStatus는 _view에서 머지)."""
    chars_by_name = {c.get("name"): c for c in character_repository.list() if c.get("name")}
    targets: list[dict] = []

    has_narration = False
    speakers: list[str] = []
    for scene in story.get("scenes", []):
        for item in scene.get("items", []):
            if not (item.get("text") or "").strip():
                continue
            if item.get("type") == "narration":
                has_narration = True
            elif item.get("type") == "dialogue":
                spk = item.get("speaker")
                if spk and spk not in speakers:
                    speakers.append(spk)

    if has_narration:
        narrator_id = story.get("narratorVoiceId")
        targets.append(
            {
                "targetType": "narration",
                "targetId": NARRATION_TARGET_ID,
                "displayName": "나레이션",
                "imageUrl": None,
                "matched": True,
                "characterName": None,
                "voiceId": narrator_id,
                "voiceName": _voice_name(narrator_id),
                "reason": None,
            }
        )

    for spk in speakers:
        char = chars_by_name.get(spk)
        if char:
            char_id = char.get("characterId")
            voice_id = char.get("voiceId")
            targets.append(
                {
                    "targetType": "character",
                    "targetId": char_id,
                    "displayName": spk,
                    "imageUrl": resolve_character_display_image(char, None),
                    "matched": True,
                    "characterName": spk,
                    "voiceId": voice_id,
                    "voiceName": _voice_name(voice_id),
                    "reason": None,
                }
            )
        else:
            # 매칭 캐릭터 없음 → 잠글 수 없는 필수 대상(캐릭터 먼저 생성해야 함)
            targets.append(
                {
                    "targetType": "character",
                    "targetId": spk,
                    "displayName": spk,
                    "imageUrl": None,
                    "matched": False,
                    "characterName": spk,
                    "voiceId": None,
                    "voiceName": None,
                    "reason": "character_not_found",
                }
            )

    return targets


def _view(story: dict) -> dict:
    """GET /voice-locks 응답 구성: 대상별 상태 + allLocked/nextStepEnabled."""
    locks_state = story.get("voiceLocks", {})
    items = []
    all_locked = True
    has_failed = False
    for target in _collect_targets(story):
        state = locks_state.get(target["targetId"], {}) if target["matched"] else {}
        lock_status = state.get("lockStatus", "unlocked")
        tts_status = state.get("ttsStatus", "idle")
        if not (target["matched"] and lock_status == "locked"):
            all_locked = False
        if tts_status == "failed":
            has_failed = True
        items.append(
            {
                "targetType": target["targetType"],
                "targetId": target["targetId"],
                "displayName": target["displayName"],
                "imageUrl": target["imageUrl"],
                "matched": target["matched"],
                "voiceId": target["voiceId"],
                "voiceName": target["voiceName"],
                "lockStatus": lock_status,
                "ttsStatus": tts_status,
                "reason": target["reason"],
            }
        )
    # 다음 단계 이동: 모든 필수 대상 locked + 실패한 대상 없음
    # (generating 은 허용 — 백그라운드 생성 중 이동 가능 / failed 는 차단)
    return {
        "storyId": story["storyId"],
        "allLocked": all_locked,
        "nextStepEnabled": all_locked and not has_failed,
        "hasFailed": has_failed,
        "voiceLocks": items,
    }


def _action_view(story: dict, target_type: str, target_id: str) -> dict:
    """lock/unlock 응답: 해당 대상 상태 + allLocked/nextStepEnabled."""
    view = _view(story)
    item = next(
        (i for i in view["voiceLocks"] if i["targetId"] == target_id and i["targetType"] == target_type),
        None,
    )
    return {
        "storyId": story["storyId"],
        "targetType": target_type,
        "targetId": target_id,
        "lockStatus": item["lockStatus"] if item else "unlocked",
        "ttsStatus": item["ttsStatus"] if item else "idle",
        "allLocked": view["allLocked"],
        "nextStepEnabled": view["nextStepEnabled"],
    }


def get_voice_locks(story_id: str) -> dict:
    story = story_repository.get(story_id)
    if story is None:
        raise StoryNotFoundError()
    return _view(story)


def _resolve_lock_target(story: dict, target_type: str, target_id: str):
    """잠글 대상의 voiceId / characterName 해석. 잘못된 대상이면 예외."""
    if target_type == "narration":
        return story.get("narratorVoiceId"), None
    if target_type == "character":
        char = character_repository.get(target_id)
        if char is None:
            raise VoiceLockTargetNotFoundError()
        return char.get("voiceId"), char.get("name")
    raise VoiceLockTargetNotFoundError()


def lock_target(story_id: str, target_type: str, target_id: str) -> dict:
    """대상 하나를 잠그고, 그 대상 item TTS 생성을 백그라운드로 시작한다."""
    story = story_repository.get(story_id)
    if story is None:
        raise StoryNotFoundError()

    voice_id, character_name = _resolve_lock_target(story, target_type, target_id)
    if not voice_id:
        raise VoiceNotConnectedError()
    if not _voice_ready(voice_id):
        raise VoiceNotReadyError()

    # 잠금 + generationToken 캡처. job 은 이 토큰일 때만 결과를 반영(해제/재잠금 race 방어).
    gen = story_repository.lock_voice_target(story_id, target_id)

    def build_result() -> dict:
        try:
            result = tts_service.generate_target_audios(story_id, target_type, character_name)
            tts_status = "ready" if result.get("readyCount", 0) > 0 else "failed"
            applied = story_repository.apply_target_tts_status(story_id, target_id, tts_status, gen)
            return {"targetId": target_id, "ttsStatus": tts_status, "applied": applied, **result}
        except Exception:  # noqa: BLE001 — 같은 토큰+locked 일 때만 failed 반영
            story_repository.apply_target_tts_status(story_id, target_id, "failed", gen)
            raise

    job_manager.run_async(
        JobType.tts_generate.value,
        build_result,
        "Target TTS generation failed",
        "Target TTS generation started.",
        payload={"storyId": story_id},  # 실패 알림도 storyId 보존(클릭→해당 timeline 이동)
    )
    return _action_view(story_repository.get(story_id), target_type, target_id)


def unlock_target(story_id: str, target_type: str, target_id: str) -> dict:
    """대상 하나의 잠금을 해제한다(ttsStatus=stale). 보이스 재연결 가능."""
    story = story_repository.get(story_id)
    if story is None:
        raise StoryNotFoundError()
    # 대상 유효성만 확인(없는 캐릭터면 404)
    _resolve_lock_target(story, target_type, target_id)

    # unlocked/stale 로. gen 은 유지 — 진행 중 job 은 lockStatus 불일치로 자동 무시됨.
    story_repository.unlock_voice_target(story_id, target_id)
    return _action_view(story_repository.get(story_id), target_type, target_id)

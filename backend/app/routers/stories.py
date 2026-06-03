from fastapi import APIRouter

from ..schemas.story import (
    NarratorVoiceResponse,
    NarratorVoiceUpdateRequest,
    StoryParseRequest,
    StoryParseResponse,
    VoiceLockActionResponse,
    VoiceLocksResponse,
)
from ..services import voice_lock_service
from ..services.story_service import story_service

router = APIRouter(prefix="/api/stories", tags=["stories"])


@router.post("/parse", response_model=StoryParseResponse, summary="대본 파싱")
def parse_story(request: StoryParseRequest):
    """
    사용자가 입력한 동화 대본을 장면(scene) 단위로 분해합니다.

    **파싱 규칙**
    - 빈 줄(공백만 있는 줄 포함) 기준으로 씬을 나눕니다.
    - `화자: "대사"` 형식(큰따옴표 필수)이면 **dialogue**로 처리합니다.
    - 그 외 모든 문장은 **narration**으로 처리합니다.
    - 형식이 맞지 않아도 에러 없이 narration으로 처리합니다.

    파싱 결과는 메모리 Mock Repository에 저장되며 storyId로 조회할 수 있습니다.
    서버 재시작 시 데이터는 초기화됩니다.
    """
    return story_service.parse_and_save(request.title, request.script)


@router.get("", response_model=list[StoryParseResponse], summary="스토리 목록 조회")
def list_stories():
    """
    메모리 Mock Repository에 저장된 스토리 목록을 전부 반환합니다.
    """
    return story_service.list_stories()


@router.get("/{story_id}", response_model=StoryParseResponse, summary="스토리 단건 조회")
def get_story(story_id: str):
    """
    storyId로 저장된 스토리 하나를 조회합니다.

    - storyId 예시: `story_mock_001`
    - 존재하지 않는 storyId 요청 시 404(Story not found)를 반환합니다.
    """
    return story_service.get_story(story_id)


@router.patch(
    "/{story_id}/narrator-voice",
    response_model=NarratorVoiceResponse,
    summary="나레이션 보이스 연결/해제",
)
def update_narrator_voice(story_id: str, request: NarratorVoiceUpdateRequest):
    """
    스토리의 나레이션 보이스를 연결하거나 해제합니다.

    - `voiceId`가 있으면 해당 보이스로 연결합니다(없는 보이스면 404 Voice not found).
      단 **`status="ready"`인 보이스만 허용**하며, ready 아니면 400(Voice not ready).
      voiceType(narrator/character)은 추천 태그일 뿐 연결을 제한하지 않습니다(character 타입도 나레이션에 연결 가능).
    - `voiceId`가 `null`이면 나레이션 보이스를 해제합니다(보이스 존재 검증 안 함).
    - 존재하지 않는 storyId면 404(Story not found)를 반환합니다.
    - TTS 생성 시 narration item의 voiceId로 이 값이 복사됩니다. (dialogue는 캐릭터 보이스)
    """
    return story_service.update_narrator_voice(story_id, request.voiceId)


@router.get(
    "/{story_id}/voice-locks",
    response_model=VoiceLocksResponse,
    summary="대상별 보이스 잠금 상태 조회",
)
def get_voice_locks(story_id: str):
    """
    나레이션/캐릭터 대상별 보이스 연결·잠금 상태를 조회합니다.

    - 각 대상: `lockStatus`(unlocked/locked) + `ttsStatus`(idle/generating/ready/failed/stale)
    - `allLocked`/`nextStepEnabled`: 모든 필수 대상이 locked 여야 true → [배경 →] 활성 기준.
    - 매칭 캐릭터가 없는 speaker는 `matched=false` + `reason=character_not_found` (잠금 불가).
    """
    return voice_lock_service.get_voice_locks(story_id)


@router.post(
    "/{story_id}/voice-locks/{target_type}/{target_id}/lock",
    response_model=VoiceLockActionResponse,
    summary="대상별 보이스 잠금 + 해당 대상 TTS 생성 시작",
)
def lock_voice_target(story_id: str, target_type: str, target_id: str):
    """
    한 대상(나레이션 또는 캐릭터)의 보이스를 잠그고, 그 대상 item 의 TTS 생성을 백그라운드로 시작합니다.

    - `target_type`: `narration` | `character`, `target_id`: `narration` 또는 characterId
    - 검증: voiceId 연결(없으면 400 voice_not_connected) + voice.status==ready(아니면 400 voice_not_ready)
    - 성공 시 lockStatus=locked, ttsStatus=generating. 진행은 GET `/voice-locks` 로 폴링.
    """
    return voice_lock_service.lock_target(story_id, target_type, target_id)


@router.post(
    "/{story_id}/voice-locks/{target_type}/{target_id}/unlock",
    response_model=VoiceLockActionResponse,
    summary="대상별 보이스 잠금 해제",
)
def unlock_voice_target(story_id: str, target_type: str, target_id: str):
    """
    한 대상의 잠금을 해제해 다시 연결을 바꿀 수 있게 합니다(ttsStatus=stale).

    다시 잠그면 그 대상 item 의 TTS 만 재생성합니다(다른 대상 audio는 유지).
    """
    return voice_lock_service.unlock_target(story_id, target_type, target_id)

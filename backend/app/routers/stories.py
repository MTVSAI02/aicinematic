from fastapi import APIRouter

from ..schemas.story import (
    NarratorVoiceResponse,
    NarratorVoiceUpdateRequest,
    StoryParseRequest,
    StoryParseResponse,
)
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
    - `voiceId`가 `null`이면 나레이션 보이스를 해제합니다(보이스 존재 검증 안 함).
    - 존재하지 않는 storyId면 404(Story not found)를 반환합니다.
    - TTS 생성 시 narration item의 voiceId로 이 값이 복사됩니다. (dialogue는 캐릭터 보이스)
    """
    return story_service.update_narrator_voice(story_id, request.voiceId)

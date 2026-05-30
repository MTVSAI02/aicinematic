from fastapi import APIRouter

from ..schemas.voice import (
    VoiceCreateRequest,
    VoiceDeleteResponse,
    VoiceResponse,
    VoiceUpdateRequest,
)
from ..services.voice_service import voice_service

router = APIRouter(prefix="/api/voices", tags=["voices"])


@router.post("", response_model=VoiceResponse, summary="보이스 자산 생성")
def create_voice(request: VoiceCreateRequest):
    """
    보이스 자산을 생성하고 voiceId를 발급한다. (현재 mock)

    캐릭터/배경처럼 재사용 가능한 라이브러리 자산이며, 캐릭터가 voiceId로 참조한다.
    실제 클로닝/샘플 합성은 AI/TTS 파트가 담당한다(현재 sampleAudioUrl 등은 null 가능).
    """
    return voice_service.create_voice(request.model_dump())


@router.get("", response_model=list[VoiceResponse], summary="보이스 목록 조회")
def list_voices():
    """저장된 보이스 라이브러리 전체를 반환한다."""
    return voice_service.list_voices()


@router.get("/{voice_id}", response_model=VoiceResponse, summary="보이스 단건 조회")
def get_voice(voice_id: str):
    """voiceId로 보이스를 조회한다. 없으면 404(Voice not found)."""
    return voice_service.get_voice(voice_id)


@router.patch("/{voice_id}", response_model=VoiceResponse, summary="보이스 수정")
def update_voice(voice_id: str, request: VoiceUpdateRequest):
    """
    보이스 메타데이터를 수정한다.

    - 없으면 404(Voice not found).
    - 기본 제공(preset) 보이스면 400(Default voice cannot be modified).
    - 수정 가능한 필드가 없으면 400(No fields to update).
    """
    return voice_service.update_voice(voice_id, request.model_dump(exclude_unset=True))


@router.delete("/{voice_id}", response_model=VoiceDeleteResponse, summary="보이스 삭제")
def delete_voice(voice_id: str):
    """
    보이스를 삭제한다.

    - 없으면 404(Voice not found).
    - 기본 제공(preset) 보이스면 400(Default voice cannot be deleted).
    - 이 voiceId를 참조하던 모든 캐릭터의 voiceId와 스토리의 narratorVoiceId를 null로 만든다.
    """
    return voice_service.delete_voice(voice_id)

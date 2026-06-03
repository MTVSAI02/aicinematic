from fastapi import APIRouter, File, Form, UploadFile

from ..schemas.voice import (
    VoiceCloneJobResponse,
    VoiceCreateRequest,
    VoiceDeleteResponse,
    VoiceResponse,
    VoiceUpdateRequest,
)
from ..services.voice_clone_service import create_voice_clone_job
from ..services.voice_sample_service import voice_sample_service
from ..services.voice_service import voice_service

router = APIRouter(prefix="/api/voices", tags=["voices"])


@router.post("/clone", response_model=VoiceCloneJobResponse, summary="보이스 클로닝 시작(업로드 음성)")
async def clone_voice(
    # 텍스트 필드는 Form(None) 으로 받고 빈값/누락 검증은 서비스에서 400 으로 처리(일관성).
    # audioFile 만 FastAPI 레벨 필수(누락 시 422).
    name: str | None = Form(None),
    voiceType: str | None = Form(None, description="narrator | character"),
    referenceText: str | None = Form(None),
    voicePrompt: str | None = Form(None),
    characterId: str | None = Form(None),
    speakerLabel: str | None = Form(None, description="누가 녹음했는지(엄마/아이/아빠 등). voiceType과 독립"),
    audioFile: UploadFile = File(...),
):
    """업로드한 reference 음성으로 보이스 클로닝 Job 을 시작한다(비동기).

    - multipart/form-data: name, voiceType, referenceText, voicePrompt?, characterId?, audioFile.
    - voiceId 발급 + reference 저장(storage/voices/{voiceId}/) 후 jobId 반환 → GET /api/jobs/{jobId} 폴링.
    - voiceType=character + characterId 있으면 그 캐릭터에 voiceId 연결(없는 캐릭터면 404).
    - 완료 시 sample.wav 저장 + voice.status=ready. 실패 시 status=failed + error. (AI 미설정/실패 → Job failed)
    - 기존 /api/tts/scene 흐름은 변경 없음.
    """
    audio_bytes = await audioFile.read()
    return create_voice_clone_job(
        name=name,
        voice_type=voiceType,
        reference_text=referenceText,
        voice_prompt=voicePrompt,
        character_id=characterId,
        speaker_label=speakerLabel,
        audio_bytes=audio_bytes,
        audio_filename=audioFile.filename,
        content_type=audioFile.content_type,
    )


@router.post("/presets/samples", response_model=list[VoiceResponse], summary="기본 나레이션 보이스 샘플 일괄 생성")
def generate_preset_voice_samples():
    """기본 나레이션 preset 4개의 sample.wav를 백엔드 storage에 저장하고 /storage URL을 반환한다."""
    return voice_sample_service.generate_preset_samples()


@router.post("/{voice_id}/sample", response_model=VoiceResponse, summary="보이스 미리듣기 샘플 생성")
def generate_voice_sample(voice_id: str):
    """AI/TTS 임시 URL을 그대로 저장하지 않고 wav bytes를 백엔드 storage에 복사 저장한다."""
    return voice_sample_service.generate_sample(voice_id)


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

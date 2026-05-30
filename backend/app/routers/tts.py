from fastapi import APIRouter

from ..schemas.job import JobCreatedResponse
from ..schemas.tts import (
    TTSAudioResponse,
    TTSDeleteResponse,
    TTSSceneGenerateRequest,
)
from ..services.tts_service import tts_service

router = APIRouter(prefix="/api/tts", tags=["tts"])


@router.post("/scene", response_model=JobCreatedResponse, summary="씬 TTS 생성 Job")
def generate_scene_tts(request: TTSSceneGenerateRequest):
    """
    storyId/sceneId의 scene.items를 기반으로 TTS 생성 Job을 만든다. (현재 mock, 즉시 completed)

    - 실제 TTS 모델 호출 없이 mock audio(audioUrl=null)를 만들어 저장한다.
    - 감정은 item.emotion/emotionLabel을 그대로 사용한다(TTS가 새로 판단하지 않음).
    - narration→voiceType=narrator, dialogue→voiceType=character.
      dialogue는 speaker로 저장 캐릭터(name 매칭)를 찾아 characterId/voiceId를 채운다(미매칭이면 null).
      narration은 characterId=null, voiceId=story.narratorVoiceId(미설정이면 null). 실제 합성/클로닝은 AI 단계.
    - 같은 scene에 대해 재생성하면 기존 TTS 결과를 교체한다.
    - story 없음→404, scene 없음→404, 생성할 item이 없으면→400.
    - 결과(audios)는 GET /api/jobs/{jobId} 또는 GET /api/tts 로 조회한다.
    """
    return tts_service.generate_scene_tts(request.storyId, request.sceneId)


@router.get("", response_model=list[TTSAudioResponse], summary="씬별 TTS 결과 조회")
def list_scene_tts(storyId: str, sceneId: str):
    """
    저장된 scene TTS 결과를 조회한다.

    - 저장소 기준 조회이며 story/scene 존재 검증을 하지 않는다.
    - 저장된 audio가 없으면 빈 배열을 반환한다(404 아님).
    """
    return tts_service.list_scene_audios(storyId, sceneId)


@router.delete("/{audio_id}", response_model=TTSDeleteResponse, summary="TTS 결과 삭제")
def delete_tts_audio(audio_id: str):
    """
    audioId로 저장된 TTS audio를 삭제한다.

    - 존재하지 않으면 404(TTS audio not found)를 반환한다.
    """
    return tts_service.delete_audio(audio_id)

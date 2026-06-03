from fastapi import APIRouter

from ..schemas.job import JobCreatedResponse
from ..schemas.tts import (
    TTSAudioResponse,
    TTSDeleteResponse,
    TTSSceneGenerateRequest,
    TTSStoryGenerateRequest,
)
from ..services.tts_service import tts_service

router = APIRouter(prefix="/api/tts", tags=["tts"])


@router.post("/scene", response_model=JobCreatedResponse, summary="씬 TTS 생성 Job")
def generate_scene_tts(request: TTSSceneGenerateRequest):
    """
    storyId/sceneId의 scene.items를 기반으로 TTS 생성 Job을 만든다.

    - 백엔드가 scene.items를 TTS_AI_CONTRACT.md의 items 형태로 구성한다.
    - AI_TTS_URL이 설정되어 있으면 POST {AI_TTS_URL}/tts로 전달한다.
    - QWEN_TTS_ENABLED=1이면 로컬 Qwen3-TTS 어댑터를 사용한다.
    - 둘 다 없으면 audioUrl=null 메타만 저장한다.
    - 감정은 item.emotion/emotionLabel을 그대로 사용한다(TTS가 새로 판단하지 않음).
    - narration→voiceType=narrator, dialogue→voiceType=character.
      dialogue는 speaker로 저장 캐릭터(name 매칭)를 찾아 characterId/voiceId를 채운다(미매칭이면 null).
      narration은 characterId=null, voiceId=story.narratorVoiceId(미설정이면 null). 실제 합성/클로닝은 AI 단계.
    - 같은 scene에 대해 재생성하면 기존 TTS 결과를 교체한다.
    - story 없음→404, scene 없음→404, 생성할 item이 없으면→400.
    - 결과(audios)는 GET /api/jobs/{jobId} 또는 GET /api/tts 로 조회한다.
    """
    return tts_service.generate_scene_tts(request.storyId, request.sceneId)


@router.post("/story", response_model=JobCreatedResponse, summary="스토리 전체 TTS 생성 Job")
def generate_story_tts(request: TTSStoryGenerateRequest):
    """
    현재 저장된 narratorVoiceId / character.voiceId 연결값을 기준으로 story 전체 scene TTS를 생성한다.

    - 프론트 /voice 의 [이 보이스 설정으로 진행하기]에서 호출한다.
    - Job은 background thread에서 실행되므로 사용자는 /background, /scene-editor로 이동해도 된다.
    - 각 scene 결과는 기존과 동일하게 audioId 기준으로 저장되고 GET /api/tts 로 조회한다.
    """
    return tts_service.generate_story_tts(request.storyId)


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

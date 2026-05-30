from ..core.exceptions import (
    EmptySceneItemsError,
    SceneNotFoundError,
    StoryNotFoundError,
    TTSAudioNotFoundError,
)
from ..repositories.character_repo import character_repository
from ..repositories.story_repo import story_repository
from ..repositories.tts_audio_repository import tts_audio_repository
from .tts_job_runner import create_tts_generation_job

# voiceType 매핑: narration → narrator, dialogue → character
VOICE_TYPE = {
    "narration": "narrator",
    "dialogue": "character",
}

# item.emotion이 비어 있을 때(과거/수동 데이터 방어) 타입별 기본 감정
DEFAULT_EMOTION = {
    "narration": ("calm", "잔잔함"),
    "dialogue": ("neutral", "기본"),
}


class TTSService:
    """scene.items 기반 TTS 생성/조회/삭제 비즈니스 로직.

    감정은 새로 판단하지 않고 item.emotion/emotionLabel을 그대로 사용한다.
    실제 TTS 모델 호출 없이 mock audio(audioUrl=None)를 만든다.
    """

    def __init__(self, story_repo, tts_audio_repo, character_repo):
        self._story_repo = story_repo
        self._tts_audio_repo = tts_audio_repo
        self._character_repo = character_repo

    def generate_scene_tts(self, story_id: str, scene_id: str) -> dict:
        scene = self._find_scene(story_id, scene_id)

        # dialogue speaker → 저장된 캐릭터(name) → characterId/voiceId 매핑 준비
        chars_by_name = {
            c.get("name"): c for c in self._character_repo.list() if c.get("name")
        }

        # scene.items → audio target 변환 (text 빈 item 제외, 원본 itemIndex 유지)
        audio_targets = []
        for index, item in enumerate(scene.get("items", [])):
            text = (item.get("text") or "").strip()
            if not text:
                continue  # 방어적: 빈 text item 제외 (itemIndex는 재번호하지 않음)

            item_type = item.get("type")
            # 방어: emotion/emotionLabel이 비면 타입별 기본값으로 보강 (응답 검증 실패 방지)
            default_emotion, default_label = DEFAULT_EMOTION.get(
                item_type, ("neutral", "기본")
            )

            # dialogue면 speaker로 캐릭터를 찾아 characterId/voiceId 반영.
            # narration이거나 매칭되는 캐릭터가 없으면 둘 다 None.
            character_id = None
            voice_id = None
            if item_type == "dialogue":
                matched = chars_by_name.get(item.get("speaker"))
                if matched:
                    character_id = matched.get("characterId")
                    voice_id = matched.get("voiceId")  # 캐릭터에 연결된 보이스 (없으면 None)

            audio_targets.append(
                {
                    "storyId": story_id,
                    "sceneId": scene_id,
                    "itemIndex": index,  # 원본 scene.items의 index 유지
                    "type": item_type,
                    "speaker": item.get("speaker"),
                    "text": item.get("text"),
                    "emotion": item.get("emotion") or default_emotion,
                    "emotionLabel": item.get("emotionLabel") or default_label,
                    "voiceType": VOICE_TYPE.get(item_type, "narrator"),
                    "characterId": character_id,
                    "voiceId": voice_id,  # 실제 합성/클로닝은 AI 파트, 여기선 참조만
                    "audioUrl": None,     # 실제 음성 파일 없음
                }
            )

        if not audio_targets:
            raise EmptySceneItemsError()

        # 재생성 정책: 같은 story+scene 기존 audio 삭제 후 새로 저장 (누적 방지)
        self._tts_audio_repo.delete_by_scene(story_id, scene_id)
        saved_audios = self._tts_audio_repo.create_many(audio_targets)

        # tts_generate Job 생성 (즉시 completed)
        return create_tts_generation_job(story_id, scene_id, saved_audios)

    def list_scene_audios(self, story_id: str, scene_id: str) -> list[dict]:
        # 조회는 story/scene 존재 검증을 하지 않는다. 저장된 게 없으면 [] 반환.
        return self._tts_audio_repo.list_by_scene(story_id, scene_id)

    def delete_audio(self, audio_id: str) -> dict:
        if self._tts_audio_repo.get(audio_id) is None:
            raise TTSAudioNotFoundError()
        self._tts_audio_repo.delete(audio_id)
        return {"deleted": True, "audioId": audio_id}

    def _find_scene(self, story_id: str, scene_id: str) -> dict:
        story = self._story_repo.get(story_id)
        if story is None:
            raise StoryNotFoundError()
        for scene in story.get("scenes", []):
            if scene.get("sceneId") == scene_id:
                return scene
        raise SceneNotFoundError()


tts_service = TTSService(story_repository, tts_audio_repository, character_repository)

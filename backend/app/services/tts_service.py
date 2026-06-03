from ..core.exceptions import (
    EmptySceneItemsError,
    SceneNotFoundError,
    StoryNotFoundError,
    TTSGenerationFailedError,
    TTSAudioNotFoundError,
)
from ..repositories.character_repo import character_repository
from ..repositories.job_repo import job_repository
from ..repositories.story_repo import story_repository
from ..repositories.tts_audio_repository import tts_audio_repository
from ..repositories.voice_repository import voice_repository
from ..schemas.job import JobType
from .job_manager import job_manager
from .tts_ai_client import tts_ai_client
from .tts_job_runner import create_tts_generation_job, create_tts_story_generation_job

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

# emotion 키 → Qwen 합성용 자연어 instruction. (Qwen3-TTS 0.6B 는 단순 키보다 instruction 이 안정적)
EMOTION_PROMPT = {
    "neutral": "Speak in a natural and neutral tone.",
    "calm": "Speak in a calm and gentle tone.",
    "happy": "Speak in a bright and happy tone.",
    "sad": "Speak in a sad and quiet tone.",
    "angry": "Speak in an angry and strong tone.",
    "scared": "Speak in a nervous and scared tone.",
    "excited": "Speak in an excited and energetic tone.",
    "friendly": "Speak in a warm and friendly tone.",
    "serious": "Speak in a serious and focused tone.",
    "curious": "Speak in a curious and gentle tone.",
}
DEFAULT_EMOTION_PROMPT = EMOTION_PROMPT["neutral"]  # 알 수 없는 emotion → neutral fallback


def _character_prompt(character: dict | None) -> str | None:
    """캐릭터 대사 합성용 prompt. 1순위 description → 2순위 appearancePrompt → 3순위 name 기반 기본 설명."""
    if not character:
        return None
    desc = (character.get("description") or "").strip()
    if desc:
        return desc
    appearance = (character.get("appearancePrompt") or "").strip()
    if appearance:
        return appearance
    return f"{character.get('name') or '캐릭터'} 캐릭터의 말투로 말합니다."

class TTSService:
    """scene.items 기반 TTS 생성/조회/삭제 비즈니스 로직.

    감정은 새로 판단하지 않고 item.emotion/emotionLabel을 그대로 사용한다.
    백엔드가 audioId를 발급하고, AI/TTS는 audioId -> audioUrl만 채운다.
    """

    def __init__(self, story_repo, tts_audio_repo, character_repo, voice_repo):
        self._story_repo = story_repo
        self._tts_audio_repo = tts_audio_repo
        self._character_repo = character_repo
        self._voice_repo = voice_repo

    def generate_scene_tts(self, story_id: str, scene_id: str) -> dict:
        saved_audios = self._generate_scene_tts_now(story_id, scene_id)
        return create_tts_generation_job(story_id, scene_id, saved_audios)

    def generate_story_tts(self, story_id: str) -> dict:
        story = self._story_repo.get(story_id)
        if story is None:
            raise StoryNotFoundError()

        def build_result() -> dict:
            return self._generate_story_tts_now(story_id, replace_existing=True)

        return create_tts_story_generation_job(story_id, build_result)

    def _generate_story_tts_now(
        self,
        story_id: str,
        *,
        replace_existing: bool,
        job_id: str | None = None,
    ) -> dict:
        story = self._story_repo.get(story_id)
        if story is None:
            raise StoryNotFoundError()

        scenes = list(story.get("scenes", []))
        scene_results = []
        all_audios = []
        total = max(len(scenes), 1)

        for index, scene in enumerate(scenes, start=1):
            scene_id = scene.get("sceneId")
            if not scene_id:
                continue
            try:
                audios = self._generate_scene_tts_now(
                    story_id,
                    scene_id,
                    replace_existing=replace_existing,
                )
            except EmptySceneItemsError:
                audios = []
            scene_results.append({"sceneId": scene_id, "audios": audios})
            all_audios.extend(audios)
            if job_id:
                progress = min(95, 10 + int((index / total) * 85))
                job_repository.update_status(job_id, "running", progress=progress)

        return {
            "storyId": story_id,
            "sceneCount": len(scene_results),
            "audioCount": len(all_audios),
            "scenes": scene_results,
            "audios": all_audios,
        }

    def _generate_scene_tts_now(
        self,
        story_id: str,
        scene_id: str,
        *,
        replace_existing: bool = True,
    ) -> list[dict]:
        audio_targets = self._build_scene_audio_targets(story_id, scene_id)
        if not audio_targets:
            raise EmptySceneItemsError()

        if replace_existing:
            # 재생성 정책: 같은 story+scene 기존 audio 삭제 후 새로 저장 (누적 방지)
            self._tts_audio_repo.delete_by_scene(story_id, scene_id)
            saved_audios = self._tts_audio_repo.create_many(audio_targets)
            pending_audios = saved_audios
        else:
            existing_by_item = {}
            for audio in self._tts_audio_repo.list_by_scene(story_id, scene_id):
                item_index = audio.get("itemIndex")
                current = existing_by_item.get(item_index)
                if current is None or (audio.get("audioUrl") and not current.get("audioUrl")):
                    existing_by_item[item_index] = audio
            saved_audios = []
            pending_audios = []
            for target in audio_targets:
                existing = existing_by_item.get(target["itemIndex"])
                if existing and existing.get("audioUrl"):
                    saved_audios.append(existing)
                    continue
                saved = self._tts_audio_repo.upsert_target(
                    target,
                    audio_id=existing.get("audioId") if existing else None,
                )
                saved_audios.append(saved)
                pending_audios.append(saved)

        if not pending_audios:
            return saved_audios

        ai_payload = {
            "storyId": story_id,
            "sceneId": scene_id,
            "items": pending_audios,
        }
        ai_result = tts_ai_client.synthesize_scene(ai_payload)
        if ai_result and isinstance(ai_result.get("audios"), list):
            self._tts_audio_repo.apply_ai_result(ai_result["audios"])
            saved_audios = self._tts_audio_repo.list_by_scene(story_id, scene_id)
        return saved_audios

    def _build_scene_audio_targets(self, story_id: str, scene_id: str) -> list[dict]:
        scene = self._find_scene(story_id, scene_id)

        # narration용 나레이터 보이스 (story 단위, 없으면 None)
        story = self._story_repo.get(story_id)
        narrator_voice_id = story.get("narratorVoiceId") if story else None

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

            # dialogue: speaker로 캐릭터를 찾아 characterId/voiceId 반영 (매칭 없으면 None).
            # narration: characterId는 없고, voiceId는 story.narratorVoiceId 사용 (없으면 None).
            character_id = None
            voice_id = None
            voice = None
            matched = None
            if item_type == "dialogue":
                matched = chars_by_name.get(item.get("speaker"))
                if matched:
                    character_id = matched.get("characterId")
                    voice_id = matched.get("voiceId")  # 캐릭터에 연결된 보이스 (없으면 None)
            elif item_type == "narration":
                voice_id = narrator_voice_id  # 나레이터 보이스 (없으면 None)
            if voice_id:
                voice = self._voice_repo.get(voice_id)
                # ready 가 아닌 voice(pending/processing/failed/삭제됨)는 합성에서 제외.
                # → voiceId/voice 를 null 처리해 AI 가 voiceType 기본 목소리로 fallback.
                if not voice or voice.get("status") != "ready":
                    voice_id = None
                    voice = None

            emotion_value = item.get("emotion") or default_emotion

            audio_targets.append(
                {
                    "storyId": story_id,
                    "sceneId": scene_id,
                    "itemIndex": index,  # 원본 scene.items의 index 유지
                    "type": item_type,
                    "speaker": item.get("speaker"),
                    "text": item.get("text"),
                    "emotion": emotion_value,
                    "emotionLabel": item.get("emotionLabel") or default_label,
                    # emotion 키 → Qwen 합성용 instruction (unknown 은 neutral fallback)
                    "emotionPrompt": EMOTION_PROMPT.get(emotion_value, DEFAULT_EMOTION_PROMPT),
                    "voiceType": VOICE_TYPE.get(item_type, "narrator"),
                    "characterId": character_id,
                    # dialogue 매칭 캐릭터 이름/말투 prompt (narration·미매칭이면 None)
                    "characterName": matched.get("name") if matched else None,
                    "characterPrompt": _character_prompt(matched),
                    "voiceId": voice_id,  # 실제 합성/클로닝은 AI 파트, 여기선 참조만
                    "voiceName": voice.get("name") if voice else None,
                    "voicePrompt": voice.get("voicePrompt") if voice else None,
                    # Qwen3-TTS 0.6B ref 기반 — AI cache miss 대비. preset/미연결이면 None.
                    # AI payload 전용(프론트 응답엔 미노출 — TTSAudioResponse 에 필드 없음).
                    "referenceAudioUrl": voice.get("referenceAudioUrl") if voice else None,
                    "referenceText": voice.get("referenceText") if voice else None,
                    "audioUrl": None,
                    "durationSec": None,
                    "error": None,
                }
            )
        return audio_targets

    def list_scene_audios(self, story_id: str, scene_id: str) -> list[dict]:
        # 조회는 story/scene 존재 검증을 하지 않는다. 저장된 게 없으면 [] 반환.
        return self._tts_audio_repo.list_by_scene(story_id, scene_id)

    def resume_unfinished_story_tts_jobs(self) -> int:
        resumed = 0
        jobs = job_repository.list_unfinished(JobType.tts_story_generate.value)
        for job in jobs:
            job_id = job.get("jobId")
            payload = job.get("payload") or {}
            story_id = job.get("storyId") or payload.get("storyId")
            if not job_id:
                continue
            if not story_id:
                job_repository.fail(job_id, "Cannot resume TTS job: storyId is missing.")
                continue
            if self._story_repo.get(story_id) is None:
                job_repository.fail(job_id, "Cannot resume TTS job: story not found.")
                continue

            def build_result(story_id=story_id, job_id=job_id) -> dict:
                return self._generate_story_tts_now(
                    story_id,
                    replace_existing=False,
                    job_id=job_id,
                )

            job_manager.resume_async(
                job_id,
                build_result,
                TTSGenerationFailedError.detail,
            )
            resumed += 1
        return resumed

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


tts_service = TTSService(
    story_repository,
    tts_audio_repository,
    character_repository,
    voice_repository,
)

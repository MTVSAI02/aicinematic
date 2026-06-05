import base64
import logging

import httpx

from ..core.config import AUDIO_STORAGE_DIR, storage_path, storage_url
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

logger = logging.getLogger(__name__)

# AI 어댑터(ngrok 등)에서 audio 다운로드 시 ngrok 무료 경고 페이지를 우회하는 헤더.
_AUDIO_DOWNLOAD_HEADERS = {"ngrok-skip-browser-warning": "1"}


def _rehost_audio_to_storage(audio: dict) -> dict:
    """AI가 준 외부 audioUrl(ngrok/ComfyUI)을 백엔드 /storage 로 복사해 브라우저가 바로 재생하게 한다.

    - 브라우저 <audio> 는 ngrok 'skip-browser-warning' 헤더를 못 붙여 경고 HTML 을 받게 됨 → 재생 불가.
      백엔드가 받아 /storage/audio/{audioId}.wav 로 저장하고 그 URL 로 바꿔 내려준다.
    - 실패(다운로드 오류/오디오 아님)하면 원본 audioUrl 을 그대로 둔다(부분 실패 허용).
    """
    url = audio.get("audioUrl")
    audio_id = audio.get("audioId")
    if not url or not audio_id:
        return audio
    try:
        resp = httpx.get(url, headers=_AUDIO_DOWNLOAD_HEADERS, timeout=120, follow_redirects=True)
        resp.raise_for_status()
        if not resp.headers.get("content-type", "").startswith("audio/"):
            logger.warning("TTS audio 재호스팅 건너뜀(오디오 아님): %s", url)
            return audio  # ngrok 경고 HTML 등 → 원본 유지(깨진 파일 저장 안 함)
        AUDIO_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        (AUDIO_STORAGE_DIR / f"{audio_id}.wav").write_bytes(resp.content)
        return {**audio, "audioUrl": storage_url("audio", f"{audio_id}.wav")}
    except Exception as exc:  # noqa: BLE001 - 실패 시 원본 URL 유지
        logger.warning("TTS audio 재호스팅 실패(%s): %s", audio_id, exc)
        return audio

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
    "worried": "Speak in a worried and careful tone.",
    "playful": "Speak in a playful and lively tone.",
    "curt": "Speak in a blunt and slightly cold tone.",
    "shy": "Speak in a shy and hesitant tone.",
    "mysterious": "Speak in a mysterious and quiet tone.",
    "disappointed": "Speak in a disappointed and subdued tone.",
}
DEFAULT_EMOTION_PROMPT = EMOTION_PROMPT["neutral"]  # 알 수 없는 emotion → neutral fallback


def _character_prompt(character: dict | None) -> str | None:
    """캐릭터 대사 합성용 prompt. 1순위 appearancePrompt → 2순위 name 기반 기본 설명."""
    if not character:
        return None
    appearance = (character.get("appearancePrompt") or "").strip()
    if appearance:
        return appearance
    return f"{character.get('name') or '캐릭터'} 캐릭터의 말투로 말합니다."


# reference 확장자 → mime (base64 동봉 시 AI 가 디코딩에 참고)
_REFERENCE_MIME = {
    "webm": "audio/webm",
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "ogg": "audio/ogg",
}


def _reference_base64(reference_url: str | None, cache: dict) -> tuple[str | None, str | None]:
    """reference /storage URL → (base64, mime). URL/파일 없으면 (None, None).

    AI 서버가 백엔드와 다른 PC 일 수 있어, cache miss 시 클론 재생성용 reference 를
    URL 대신 base64 로 동봉한다(AI 가 백엔드 storage 에 접근 못 해도 됨).
    같은 reference 는 호출당 한 번만 인코딩(파일 I/O 절약).
    """
    if not reference_url:
        return (None, None)
    if reference_url in cache:
        return cache[reference_url]
    path = storage_path(reference_url)
    if path is None or not path.exists():
        result: tuple[str | None, str | None] = (None, None)
    else:
        ext = path.suffix.lstrip(".").lower()
        mime = _REFERENCE_MIME.get(ext, "application/octet-stream")
        result = (base64.b64encode(path.read_bytes()).decode("ascii"), mime)
    cache[reference_url] = result
    return result


def _to_ai_item(audio: dict, cache: dict) -> dict:
    """AI 합성 요청용 item 변환: referenceAudioUrl → referenceAudioBase64(+ referenceAudioMime).

    base64 는 DB 에 저장하지 않고 outbound payload 에만 싣는다(저장은 lean 유지).
    """
    b64, mime = _reference_base64(audio.get("referenceAudioUrl"), cache)
    item = {k: v for k, v in audio.items() if k != "referenceAudioUrl"}
    item["referenceAudioBase64"] = b64
    item["referenceAudioMime"] = mime
    return item


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

    def _scene_context(self, story_id: str):
        """씬 합성용 컨텍스트: (narrator_voice_id, name→character 매핑)."""
        story = self._story_repo.get(story_id)
        narrator_voice_id = story.get("narratorVoiceId") if story else None
        chars_by_name = {
            c.get("name"): c for c in self._character_repo.list() if c.get("name")
        }
        return narrator_voice_id, chars_by_name

    def _build_item_target(
        self, story_id, scene_id, index, item, narrator_voice_id, chars_by_name
    ) -> dict | None:
        """단일 item → AI 합성용 target dict. text 빈 item 은 None 반환(원본 itemIndex 유지).

        narration은 story.narratorVoiceId, dialogue는 speaker로 매칭된 캐릭터의 voiceId를 참조.
        연결된 voice가 없거나 ready가 아니면 voiceId=None → AI가 voiceType 기본 목소리로 fallback.
        """
        text = (item.get("text") or "").strip()
        if not text:
            return None

        item_type = item.get("type")
        default_emotion, default_label = DEFAULT_EMOTION.get(item_type, ("neutral", "기본"))

        character_id = None
        voice_id = None
        voice = None
        matched = None
        if item_type == "dialogue":
            matched = chars_by_name.get(item.get("speaker"))
            if matched:
                character_id = matched.get("characterId")
                voice_id = matched.get("voiceId")
        elif item_type == "narration":
            voice_id = narrator_voice_id
        if voice_id:
            voice = self._voice_repo.get(voice_id)
            if not voice or voice.get("status") != "ready":
                voice_id = None
                voice = None

        emotion_value = item.get("emotion") or default_emotion
        return {
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
            # Qwen3-TTS 0.6B ref 기반 — AI cache miss 대비(프론트 응답엔 미노출).
            "referenceAudioUrl": voice.get("referenceAudioUrl") if voice else None,
            "referenceText": voice.get("referenceText") if voice else None,
            "audioUrl": None,
            "durationSec": None,
            "error": None,
        }

    def _scene_audio_targets(self, story_id: str, scene: dict) -> list[dict]:
        """scene.items 전체 → AI 합성용 target 목록."""
        narrator_voice_id, chars_by_name = self._scene_context(story_id)
        scene_id = scene.get("sceneId")
        targets = []
        for index, item in enumerate(scene.get("items", [])):
            target = self._build_item_target(
                story_id, scene_id, index, item, narrator_voice_id, chars_by_name
            )
            if target:
                targets.append(target)
        return targets

    def _call_ai_and_rehost(self, story_id, scene_id, saved_audios) -> list[dict]:
        """저장된 audios(audioId 포함)로 AI 합성 → 외부 audioUrl을 /storage로 재호스팅 → 반영.

        해당 audioId 레코드들의 최신 상태를 반환한다. (다른 audio는 건드리지 않음)
        """
        if not saved_audios:
            return []
        # referenceAudioUrl → referenceAudioBase64 (AI가 다른 PC여도 cache miss 재생성 가능).
        # 같은 reference 는 1회만 인코딩(ref_cache). base64 는 outbound payload 에만.
        ref_cache: dict = {}
        ai_items = [_to_ai_item(a, ref_cache) for a in saved_audios]
        ai_payload = {"storyId": story_id, "sceneId": scene_id, "items": ai_items}
        ai_result = tts_ai_client.synthesize_scene(ai_payload)
        if ai_result and isinstance(ai_result.get("audios"), list):
            rehosted = [_rehost_audio_to_storage(a) for a in ai_result["audios"]]
            self._tts_audio_repo.apply_ai_result(rehosted)
        return [self._tts_audio_repo.get(a["audioId"]) for a in saved_audios]

    def _synthesize_targets(
        self, story_id: str, scene_id: str, audio_targets: list[dict]
    ) -> list[dict]:
        """씬 전체 재생성용(씬 단건 TTS 엔드포인트 전용): 씬 audio 전체 삭제 후 새로 저장+합성."""
        self._tts_audio_repo.delete_by_scene(story_id, scene_id)
        saved = self._tts_audio_repo.create_many(audio_targets)
        self._call_ai_and_rehost(story_id, scene_id, saved)
        return self._tts_audio_repo.list_by_scene(story_id, scene_id)

    def _synthesize_targets_incremental(
        self, story_id: str, scene_id: str, audio_targets: list[dict]
    ) -> list[dict]:
        """재개용: 이미 audioUrl 있는 item은 스킵하고 없는 것만 생성한다.

        서버 재시작 후 pending/running job 복구 시 호출. 중복 audio row는 audioUrl 있는 것 우선.
        """
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

        if pending_audios:
            self._call_ai_and_rehost(story_id, scene_id, pending_audios)
        return self._tts_audio_repo.list_by_scene(story_id, scene_id)

    def generate_scene_tts(self, story_id: str, scene_id: str) -> dict:
        scene = self._find_scene(story_id, scene_id)
        audio_targets = self._scene_audio_targets(story_id, scene)
        if not audio_targets:
            raise EmptySceneItemsError()
        saved_audios = self._synthesize_targets(story_id, scene_id, audio_targets)
        # tts_generate Job 생성 (즉시 completed)
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
                audio_targets = self._scene_audio_targets(story_id, scene)
                if not audio_targets:
                    audios = []
                elif replace_existing:
                    audios = self._synthesize_targets(story_id, scene_id, audio_targets)
                else:
                    audios = self._synthesize_targets_incremental(story_id, scene_id, audio_targets)
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

    @staticmethod
    def _item_matches_target(item: dict, target_type: str, character_name: str | None) -> bool:
        if target_type == "narration":
            return item.get("type") == "narration"
        return item.get("type") == "dialogue" and item.get("speaker") == character_name

    def generate_target_audios(
        self, story_id: str, target_type: str, character_name: str | None = None
    ) -> dict:
        """대상별 TTS 생성(보이스 잠금 시 백그라운드 job에서 호출).

        그 대상 item만 다룬다 — 다른 대상(다른 캐릭터/나레이션) audio는 유지.
        **원자성**: 기존 audio를 먼저 지우지 않고 새로 생성한다.
          - 성공(하나라도 ready): 기존 audio 삭제 후 교체(success-after-replace)
          - 실패(예외 또는 전부 audioUrl 없음): 새로 만든 것 제거, 기존 ready audio 보존
        narration: type==narration 전체.  character: speaker==character_name 인 dialogue.
        """
        story = self._story_repo.get(story_id)
        if story is None:
            raise StoryNotFoundError()
        narrator_voice_id, chars_by_name = self._scene_context(story_id)

        # 교체 전 기존 대상 audioId (성공 시에만 삭제)
        old_ids = [
            a["audioId"]
            for a in self._tts_audio_repo.list_by_story(story_id)
            if self._item_matches_target(a, target_type, character_name)
        ]
        new_ids: list[str] = []
        audio_count = 0
        ready_count = 0
        try:
            for scene in story.get("scenes", []):
                scene_id = scene.get("sceneId")
                targets = []
                for index, item in enumerate(scene.get("items", [])):
                    if not self._item_matches_target(item, target_type, character_name):
                        continue
                    target = self._build_item_target(
                        story_id, scene_id, index, item, narrator_voice_id, chars_by_name
                    )
                    if target:
                        targets.append(target)
                if not targets:
                    continue
                saved = self._tts_audio_repo.create_many(targets)
                new_ids.extend(a["audioId"] for a in saved)
                for audio in self._call_ai_and_rehost(story_id, scene_id, saved):
                    audio_count += 1
                    if audio and audio.get("audioUrl") and not audio.get("error"):
                        ready_count += 1
        except Exception:  # noqa: BLE001 — 새로 만든 것만 정리하고 기존 audio 보존 후 재전파
            for audio_id in new_ids:
                self._tts_audio_repo.delete(audio_id)
            raise

        if ready_count > 0:
            # 성공: 기존 대상 audio 교체
            for audio_id in old_ids:
                self._tts_audio_repo.delete(audio_id)
            return {
                "audioCount": audio_count,
                "readyCount": ready_count,
                "failedCount": audio_count - ready_count,
                "replaced": True,
            }

        # 전부 실패(예외 없이 audioUrl 0개): 새 것 제거, 기존 ready audio 보존
        for audio_id in new_ids:
            self._tts_audio_repo.delete(audio_id)
        return {"audioCount": 0, "readyCount": 0, "failedCount": len(new_ids), "replaced": False}

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

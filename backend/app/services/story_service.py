from ..core.exceptions import (
    InvalidNarratorVoiceError,
    StoryNotFoundError,
    VoiceNotFoundError,
)
from ..repositories.character_repo import character_repository
from ..repositories.story_repo import story_repository
from ..repositories.voice_repository import voice_repository
from .image_resolve import resolve_character_display_image
from .story_parser import parse_script_to_scenes
from .text_overlay_service import build_text_overlays


def _serialize_story(story: dict) -> dict:
    """응답용 직렬화: 각 scene에 파생 자막(textOverlays)과, 씬 캐릭터의 표시 imageUrl을 끼워 넣는다.

    - 자막: items+subtitleSettings로 백엔드가 단일 소스 조립(프론트는 렌더만).
    - 캐릭터 표시 이미지: poseId 적용 시 포즈 이미지로 해석해 내려준다(프론트가 poses 전체를 들 필요 없음).
    저장 dict는 건드리지 않도록 얕은 복사본만 만든다(파생값을 저장소에 남기지 않음).
    """
    scenes = []
    for sc in story.get("scenes", []):
        chars = [
            {
                **ch,
                "imageUrl": resolve_character_display_image(
                    character_repository.get(ch.get("characterId")), ch.get("poseId")
                ),
            }
            for ch in sc.get("characters", [])
        ]
        scenes.append({**sc, "characters": chars, "textOverlays": build_text_overlays(sc)})
    return {**story, "scenes": scenes}


class StoryService:
    """스토리 비즈니스 로직.

    라우터가 repository를 직접 다루거나 HTTPException을 직접 던지지 않도록
    파싱/저장/조회를 이 서비스가 담당하고, 없는 스토리는 공통 예외로 변환한다.
    """

    def __init__(self, story_repo, voice_repo):
        self._story_repo = story_repo
        self._voice_repo = voice_repo

    def parse_and_save(self, title: str, script: str) -> dict:
        scenes = parse_script_to_scenes(script)
        return _serialize_story(self._story_repo.save({"title": title, "scenes": scenes}))

    def list_stories(self) -> list[dict]:
        return [_serialize_story(s) for s in self._story_repo.list()]

    def get_story(self, story_id: str) -> dict:
        story = self._story_repo.get(story_id)
        if story is None:
            raise StoryNotFoundError()
        return _serialize_story(story)

    def update_narrator_voice(self, story_id: str, voice_id: str | None) -> dict:
        """나레이션 보이스를 연결/해제한다.

        voiceId가 있으면 그 보이스 존재(없으면 VoiceNotFoundError)와
        voiceType=="narrator"(아니면 InvalidNarratorVoiceError)를 검증한다.
        null이면 검증 없이 해제한다. (캐릭터용 character 타입 보이스는 나레이터로 못 붙임)
        """
        if self._story_repo.get(story_id) is None:
            raise StoryNotFoundError()
        if voice_id is not None:
            voice = self._voice_repo.get(voice_id)
            if voice is None:
                raise VoiceNotFoundError()
            if voice.get("voiceType") != "narrator":
                raise InvalidNarratorVoiceError()
        updated = self._story_repo.set_narrator_voice(story_id, voice_id)
        return {
            "storyId": updated["storyId"],
            "narratorVoiceId": updated["narratorVoiceId"],
        }


story_service = StoryService(story_repository, voice_repository)

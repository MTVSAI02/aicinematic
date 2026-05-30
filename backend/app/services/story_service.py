from ..core.exceptions import (
    InvalidNarratorVoiceError,
    StoryNotFoundError,
    VoiceNotFoundError,
)
from ..repositories.story_repo import story_repository
from ..repositories.voice_repository import voice_repository
from .story_parser import parse_script_to_scenes


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
        return self._story_repo.save({"title": title, "scenes": scenes})

    def list_stories(self) -> list[dict]:
        return self._story_repo.list()

    def get_story(self, story_id: str) -> dict:
        story = self._story_repo.get(story_id)
        if story is None:
            raise StoryNotFoundError()
        return story

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

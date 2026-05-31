class StoryRepository:
    def __init__(self):
        self._stories: dict = {}
        self._counter: int = 0

    def save(self, story_data: dict) -> dict:
        self._counter += 1
        story_id = f"story_mock_{self._counter:03d}"
        # narratorVoiceId 기본 None (나레이션 보이스 미연결)
        saved = {"narratorVoiceId": None, **story_data, "storyId": story_id}
        self._stories[story_id] = saved
        return saved

    def get(self, story_id: str) -> dict | None:
        return self._stories.get(story_id)

    def list(self) -> list[dict]:
        return list(self._stories.values())

    def set_narrator_voice(self, story_id: str, voice_id: str | None) -> dict | None:
        """story.narratorVoiceId를 설정/해제한다. 없는 story면 None 반환."""
        story = self._stories.get(story_id)
        if story is None:
            return None
        story["narratorVoiceId"] = voice_id
        return story

    def detach_narrator_voice(self, voice_id: str) -> None:
        """주어진 voiceId를 나레이터로 쓰던 모든 story의 narratorVoiceId를 null로.

        (보이스 삭제 캐스케이드용 — character_repo.detach_voice와 대칭)
        """
        for story in self._stories.values():
            if story.get("narratorVoiceId") == voice_id:
                story["narratorVoiceId"] = None


story_repository = StoryRepository()

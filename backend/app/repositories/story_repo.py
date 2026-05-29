class StoryRepository:
    def __init__(self):
        self._stories: dict = {}
        self._counter: int = 0

    def save(self, story_data: dict) -> dict:
        self._counter += 1
        story_id = f"story_mock_{self._counter:03d}"
        saved = {**story_data, "storyId": story_id}
        self._stories[story_id] = saved
        return saved

    def get(self, story_id: str) -> dict | None:
        return self._stories.get(story_id)

    def list(self) -> list[dict]:
        return list(self._stories.values())


story_repository = StoryRepository()

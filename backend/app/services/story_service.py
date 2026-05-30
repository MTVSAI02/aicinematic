from ..core.exceptions import StoryNotFoundError
from ..repositories.story_repo import story_repository
from .story_parser import parse_script_to_scenes


class StoryService:
    """스토리 비즈니스 로직.

    라우터가 repository를 직접 다루거나 HTTPException을 직접 던지지 않도록
    파싱/저장/조회를 이 서비스가 담당하고, 없는 스토리는 공통 예외로 변환한다.
    """

    def __init__(self, story_repo):
        self._story_repo = story_repo

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


story_service = StoryService(story_repository)

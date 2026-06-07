from ..core.config import storage_path
from ..core.exceptions import (
    StoryNotFoundError,
    VoiceNotFoundError,
    VoiceNotReadyError,
)
from ..repositories.character_repo import character_repository
from ..repositories.story_repo import story_repository
from ..repositories.voice_repository import voice_repository
from .image_resolve import resolve_character_display_image
from .story_parser import EMOTION_OPTIONS, parse_story
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

    def parse_and_save(self, request) -> dict:
        """StoryParseRequest 를 inputMode(raw/structured)에 따라 파싱·저장한다.

        작성 중 데이터는 저장하지 않고, 이 호출(=씬 분해/다음 단계)에서만 새 story 를 생성한다.
        """
        scenes = parse_story(request.model_dump())
        return _serialize_story(
            self._story_repo.save({"title": request.title.strip(), "scenes": scenes})
        )

    def list_emotions(self) -> list[dict]:
        """감정 셀렉터 옵션(label/value). EMOTION_MAP 기준 전체 라벨."""
        return EMOTION_OPTIONS

    def list_stories(self) -> list[dict]:
        return [_serialize_story(s) for s in self._story_repo.list()]

    def get_story(self, story_id: str) -> dict:
        story = self._story_repo.get(story_id)
        if story is None:
            raise StoryNotFoundError()
        return _serialize_story(story)

    def delete_story(self, story_id: str) -> dict:
        """스토리 + 하위 산출물(씬/음성/영상) 삭제. 없으면 404.

        DB 는 FK CASCADE 로 정리되고, 여기선 storage 파일(TTS 오디오 + 렌더 mp4)을 정리한다.
        캐릭터/배경은 공용 라이브러리라 삭제하지 않는다.
        """
        removed = self._story_repo.delete(story_id)
        if removed is None:
            raise StoryNotFoundError()
        for url in [*removed.get("audioUrls", []), *removed.get("videoUrls", [])]:
            path = storage_path(url)
            if path is not None:
                path.unlink(missing_ok=True)
        return {"deleted": True, "storyId": story_id}

    def update_narrator_voice(self, story_id: str, voice_id: str | None) -> dict:
        """나레이션 보이스를 연결/해제한다.

        voiceId가 있으면 보이스 존재(없으면 VoiceNotFoundError)와 status=="ready"만 검증한다.
        voiceType 은 연결을 제한하지 않는다(추천 태그일 뿐) — character 타입도 나레이션에 연결 가능.
        null이면 검증 없이 해제한다.
        """
        if self._story_repo.get(story_id) is None:
            raise StoryNotFoundError()
        if voice_id is not None:
            voice = self._voice_repo.get(voice_id)
            if voice is None:
                raise VoiceNotFoundError()
            if voice.get("status") != "ready":
                raise VoiceNotReadyError()
        updated = self._story_repo.set_narrator_voice(story_id, voice_id)
        return {
            "storyId": updated["storyId"],
            "narratorVoiceId": updated["narratorVoiceId"],
        }


story_service = StoryService(story_repository, voice_repository)

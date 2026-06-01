from ..core.exceptions import (
    CharacterNotFoundError,
    InvalidCharacterVoiceError,
    NoFieldsToUpdateError,
    SceneNotFoundError,
    StoryNotFoundError,
    VoiceNotFoundError,
)
from ..repositories.character_repo import character_repository
from ..repositories.story_repo import story_repository
from ..repositories.voice_repository import voice_repository

# 캐릭터 생성용 prompt 접두 규칙. 사용자 appearancePrompt 앞에 붙는다.
# (내장 ai의 _tags_to_prompt에 있던 로직을 backend로 옮김 — AI 서버에는 이 최종 prompt만 보낸다.)
CHARACTER_PROMPT_PREFIX = "A single character, full body, standing, white background."


def build_character_final_prompt(appearance_prompt: str) -> str:
    """appearancePrompt를 외부 AI 서버에 보낼 최종 캐릭터 prompt로 조립한다.

    description은 포함하지 않는다(저장/표시용 메타데이터). 배경의 assemble_final_prompt 와 대칭.
    """
    return f"{CHARACTER_PROMPT_PREFIX} {appearance_prompt.strip()}"


# 씬에 새 캐릭터 추가 시 기본 x(중심, 정규화) — 겹치지 않게 분산. index는 추가 전 캐릭터 수.
_DEFAULT_LAYOUT_X = [0.5, 0.3, 0.7, 0.2, 0.5, 0.8]


def _default_character_layout(index: int) -> dict:
    """씬 합성 미리보기용 기본 배치. 1명=중앙 하단, 추가될수록 좌우로 분산."""
    x = _DEFAULT_LAYOUT_X[index] if index < len(_DEFAULT_LAYOUT_X) else 0.5
    # 프레임 안에 들어오도록 보수적 기본값(키 큰 캐릭터도 안 넘치게). 사용자가 드래그/리사이즈로 조정.
    return {"x": x, "y": 0.55, "scale": 0.28, "rotation": 0.0, "zIndex": index + 1, "flipX": False}


class CharacterService:
    """캐릭터 라이브러리 + 씬-캐릭터 연결 비즈니스 로직.

    라우터가 repository를 직접 다루지 않도록 CRUD를 이 서비스가 담당한다.
    존재하지 않는 대상 등 비즈니스 예외는 커스텀 예외로 발생시키고,
    HTTP 변환은 글로벌 exception handler가 담당한다.
    """

    def __init__(self, character_repo, voice_repo, story_repo):
        self._character_repo = character_repo
        self._voice_repo = voice_repo
        self._story_repo = story_repo

    def create_character(self, character_data: dict) -> dict:
        """이미 만들어진 캐릭터 결과를 직접 저장한다."""
        return self._character_repo.save(character_data)

    def list_characters(self) -> list[dict]:
        return self._character_repo.list()

    def get_character(self, character_id: str) -> dict:
        character = self._character_repo.get(character_id)
        if character is None:
            raise CharacterNotFoundError()
        return character

    def update_character(self, character_id: str, update_data: dict) -> dict:
        if not update_data:
            raise NoFieldsToUpdateError()
        updated = self._character_repo.update(character_id, update_data)
        if updated is None:
            raise CharacterNotFoundError()
        return updated

    def delete_character(self, character_id: str) -> None:
        deleted = self._character_repo.delete(character_id)
        if not deleted:
            raise CharacterNotFoundError()
        # 참조 해제: 이 캐릭터를 연결하던 모든 scene의 characterId를 null로 (배경 삭제와 대칭)
        self._detach_character_from_scenes(character_id)

    def update_character_voice(self, character_id: str, voice_id: str | None) -> dict:
        """캐릭터에 보이스(voiceId)를 연결/해제한다.

        voice_id가 주어지면 보이스 존재 + voiceType=="character"를 검증한다
        (narrator preset을 캐릭터에 붙이는 API 직접 호출 방지). None이면 연결 해제.
        캐릭터가 없으면 CharacterNotFoundError.
        """
        if voice_id is not None:
            voice = self._voice_repo.get(voice_id)
            if voice is None:
                raise VoiceNotFoundError()
            if voice.get("voiceType") != "character":
                raise InvalidCharacterVoiceError()
        updated = self._character_repo.set_voice(character_id, voice_id)
        if updated is None:
            raise CharacterNotFoundError()
        return updated

    # ── 씬-캐릭터 연결 (씬당 다중) ─────────────────────────────
    def connect_scene_character(
        self,
        story_id: str,
        scene_id: str,
        character_id: str,
        scene_appearance_prompt: str | None = None,
        layout: dict | None = None,
    ) -> dict:
        """씬에 캐릭터를 추가/수정한다. (씬당 여러 명 가능)

        story 없음 → 404, scene 없음 → 404, 캐릭터 없음 → 404.
        같은 characterId가 이미 있으면 전달된 값만 부분 갱신한다
        (sceneAppearancePrompt / layout 각각 None이 아니면 갱신 → 드래그 저장 시 prompt 안 지워짐).
        새로 추가될 때 layout이 없으면 기본 배치(겹치지 않게 분산)를 넣는다.
        반환: 그 씬의 전체 캐릭터 목록.
        """
        scene = self._find_scene(story_id, scene_id)
        if self._character_repo.get(character_id) is None:
            raise CharacterNotFoundError()

        characters = scene.setdefault("characters", [])
        existing = next(
            (c for c in characters if c.get("characterId") == character_id), None
        )
        if existing is not None:
            if scene_appearance_prompt is not None:
                existing["sceneAppearancePrompt"] = scene_appearance_prompt
            if layout is not None:
                existing["layout"] = layout
        else:
            characters.append(
                {
                    "characterId": character_id,
                    "sceneAppearancePrompt": scene_appearance_prompt,
                    "layout": layout
                    if layout is not None
                    else _default_character_layout(len(characters)),
                }
            )
        return {"storyId": story_id, "sceneId": scene_id, "characters": characters}

    def disconnect_scene_character(
        self, story_id: str, scene_id: str, character_id: str
    ) -> dict:
        """씬에서 캐릭터 1명을 제거한다. (없어도 에러 아님 — idempotent)

        story 없음 → 404, scene 없음 → 404. 반환: 남은 캐릭터 목록.
        """
        scene = self._find_scene(story_id, scene_id)
        scene["characters"] = [
            c
            for c in scene.get("characters", [])
            if c.get("characterId") != character_id
        ]
        return {
            "storyId": story_id,
            "sceneId": scene_id,
            "characters": scene["characters"],
        }

    def _find_scene(self, story_id: str, scene_id: str) -> dict:
        story = self._story_repo.get(story_id)
        if story is None:
            raise StoryNotFoundError()
        for scene in story.get("scenes", []):
            if scene.get("sceneId") == scene_id:
                return scene
        raise SceneNotFoundError()

    def _detach_character_from_scenes(self, character_id: str) -> None:
        """캐릭터 삭제 시 모든 씬의 characters 목록에서 제거 (배경 삭제와 대칭)."""
        for story in self._story_repo.list():
            for scene in story.get("scenes", []):
                if "characters" in scene:
                    scene["characters"] = [
                        c
                        for c in scene["characters"]
                        if c.get("characterId") != character_id
                    ]


character_service = CharacterService(
    character_repository, voice_repository, story_repository
)

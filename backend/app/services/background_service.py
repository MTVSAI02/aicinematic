from ..core.exceptions import (
    BackgroundCandidateNotFoundError,
    BackgroundNotFoundError,
    NoFieldsToUpdateError,
    SceneNotFoundError,
    StoryNotFoundError,
)
from ..repositories.background_candidate_repository import background_candidate_repository
from ..repositories.background_repository import background_repository
from ..repositories.story_repo import story_repository

# 배경 프롬프트 공통 규칙 (LLM 전 단계, 규칙 기반)
BACKGROUND_SUFFIX = (
    "storybook background, soft painterly style, clean composition, "
    "background only, no characters"
)
DEFAULT_NEGATIVE_PROMPT = (
    "characters, people, animals, text, watermark, blurry, low quality"
)
DEFAULT_SUGGESTED_PROMPT = "따뜻하고 부드러운 동화풍 배경"

# sourceText 키워드 → 배경 표현 매핑 (등장 순서대로 검사, 값은 중복 제거)
KEYWORD_MAP: list[tuple[tuple[str, ...], str]] = [
    (("사막",), "조용한 사막"),
    (("별빛", "별", "밤"), "별빛이 비치는 밤하늘"),
    (("숲", "나무"), "푸른 숲과 나무들"),
    (("바다", "파도"), "잔잔한 바다와 파도"),
    (("성", "궁전"), "동화 속 성과 궁전"),
    (("마을", "집"), "아늑한 작은 마을"),
    (("눈", "겨울"), "눈이 내리는 겨울 풍경"),
    (("비", "우산"), "비가 내리는 촉촉한 거리"),
    (("노을", "저녁"), "따뜻한 노을빛 하늘"),
    (("아침", "햇살"), "부드러운 아침 햇살"),
]


def assemble_final_prompt(prompt: str) -> str:
    """사용자/추천 prompt에 background only 규칙 suffix를 붙여 finalPrompt를 만든다."""
    return f"{prompt.strip()}, {BACKGROUND_SUFFIX}"


def resolve_negative_prompt(negative: str | None) -> str:
    """negativePrompt가 비어 있으면 기본값을 사용한다."""
    if negative and negative.strip():
        return negative.strip()
    return DEFAULT_NEGATIVE_PROMPT


class BackgroundService:
    """배경 프롬프트 추천 / 라이브러리 CRUD / 씬-배경 연결 비즈니스 로직."""

    def __init__(self, story_repo, candidate_repo, background_repo):
        self._story_repo = story_repo
        self._candidate_repo = candidate_repo
        self._background_repo = background_repo

    # ── 프롬프트 추천 ────────────────────────────────────────

    def suggest_prompt(self, story_id: str, scene_id: str) -> dict:
        scene = self._find_scene(story_id, scene_id)

        source_text = self._build_source_text(scene)
        suggested_prompt = self._build_suggested_prompt(source_text)

        return {
            "storyId": story_id,
            "sceneId": scene_id,
            "sourceText": source_text,
            "suggestedPrompt": suggested_prompt,
            "finalPrompt": assemble_final_prompt(suggested_prompt),
            "negativePrompt": DEFAULT_NEGATIVE_PROMPT,
        }

    @staticmethod
    def _build_source_text(scene: dict) -> str:
        items = scene.get("items", [])
        # narration 우선, 없으면 dialogue 사용
        narration = [i["text"] for i in items if i.get("type") == "narration"]
        texts = narration or [i["text"] for i in items if i.get("type") == "dialogue"]
        return " ".join(t for t in texts if t).strip()

    @staticmethod
    def _build_suggested_prompt(source_text: str) -> str:
        matched: list[str] = []
        for keywords, value in KEYWORD_MAP:
            if any(kw in source_text for kw in keywords) and value not in matched:
                matched.append(value)
        if not matched:
            return DEFAULT_SUGGESTED_PROMPT
        return ", ".join(matched) + ", 따뜻하고 신비로운 동화풍 배경"

    # ── 라이브러리 저장/조회/수정/삭제 ───────────────────────

    def save_background(self, candidate_id: str, name: str) -> dict:
        candidate = self._candidate_repo.get(candidate_id)
        if candidate is None:
            raise BackgroundCandidateNotFoundError()

        return self._background_repo.save(
            {
                "name": name,
                "prompt": candidate["prompt"],
                "finalPrompt": candidate["finalPrompt"],
                "negativePrompt": candidate["negativePrompt"],
                "imageUrl": candidate["imageUrl"],
            }
        )

    def list_backgrounds(self) -> list[dict]:
        return self._background_repo.list()

    def get_background(self, background_id: str) -> dict:
        background = self._background_repo.get(background_id)
        if background is None:
            raise BackgroundNotFoundError()
        return background

    def update_background(self, background_id: str, update_data: dict) -> dict:
        if not update_data:
            raise NoFieldsToUpdateError()
        updated = self._background_repo.update(background_id, update_data)
        if updated is None:
            raise BackgroundNotFoundError()
        return updated

    def delete_background(self, background_id: str) -> dict:
        deleted = self._background_repo.delete(background_id)
        if not deleted:
            raise BackgroundNotFoundError()

        # 참조 해제: 모든 story의 모든 scene을 순회해 backgroundId를 null로 만든다.
        self._detach_background_from_scenes(background_id)
        return {"deleted": True, "backgroundId": background_id}

    def _detach_background_from_scenes(self, background_id: str) -> None:
        for story in self._story_repo.list():
            for scene in story.get("scenes", []):
                if scene.get("backgroundId") == background_id:
                    scene["backgroundId"] = None

    # ── 씬-배경 연결 ─────────────────────────────────────────

    def connect_scene_background(
        self, story_id: str, scene_id: str, background_id: str
    ) -> dict:
        scene = self._find_scene(story_id, scene_id)

        if self._background_repo.get(background_id) is None:
            raise BackgroundNotFoundError()

        scene["backgroundId"] = background_id
        return {
            "storyId": story_id,
            "sceneId": scene_id,
            "backgroundId": background_id,
        }

    # ── 내부 헬퍼 ────────────────────────────────────────────

    def _find_scene(self, story_id: str, scene_id: str) -> dict:
        story = self._story_repo.get(story_id)
        if story is None:
            raise StoryNotFoundError()
        for scene in story.get("scenes", []):
            if scene.get("sceneId") == scene_id:
                return scene
        raise SceneNotFoundError()


background_service = BackgroundService(
    story_repository,
    background_candidate_repository,
    background_repository,
)

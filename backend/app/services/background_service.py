from ..core.config import (
    BACKGROUND_LIBRARY_STORAGE_DIR,
    storage_url,
)
from ..core.exceptions import (
    BackgroundNotFoundError,
    NoFieldsToUpdateError,
    SceneNotFoundError,
    StoryNotFoundError,
)
from ..repositories.background_repository import background_repository
from ..repositories.story_repo import story_repository

# 배경 프롬프트 공통 규칙 (LLM 전 단계, 규칙 기반)
BACKGROUND_SUFFIX = (
    "storybook background, soft painterly style, clean composition, "
    "background only, no characters"
)
# negativePrompt는 backend가 다루지 않는다. (AI FastAPI 서버/ComfyUI 워크플로 내부 고정값)
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


class BackgroundService:
    """배경 프롬프트 추천 / 라이브러리 CRUD / 씬-배경 연결 비즈니스 로직."""

    def __init__(self, story_repo, background_repo):
        self._story_repo = story_repo
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

    def save_generated_background(
        self,
        image_bytes: bytes,
        prompt: str,
        final_prompt: str,
        name: str,
        ai_image_path: str | None = None,
    ) -> dict:
        """생성된 배경 이미지 1장을 곧바로 라이브러리에 저장한다(후보 단계 없음).

        backgroundId 발급 → library 경로에 이미지 저장 → record 저장 순.
        ai_image_path: AI 서버 원본 경로(확장 대비 보관, 배경엔 현재 미사용·내부 전용).
        (background_job_runner 가 AI 생성 결과로 호출 — 사용자 선택/이름 입력 단계 제거)
        """
        background_id = self._background_repo.reserve_id()
        BACKGROUND_LIBRARY_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        (BACKGROUND_LIBRARY_STORAGE_DIR / f"{background_id}.png").write_bytes(image_bytes)
        image_url = storage_url("backgrounds", "library", f"{background_id}.png")
        return self._background_repo.create(
            background_id,
            {
                "name": name,
                "prompt": prompt,
                "finalPrompt": final_prompt,
                "imageUrl": image_url,
                "aiImagePath": ai_image_path,
            },
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

        # 저장본 이미지 파일도 함께 삭제 (record만 지우면 library 파일이 고아로 남음).
        (BACKGROUND_LIBRARY_STORAGE_DIR / f"{background_id}.png").unlink(missing_ok=True)
        # scene.backgroundId 참조는 FK ondelete=SET NULL 이 자동 정리(배경 row 삭제 → 참조 null).
        return {"deleted": True, "backgroundId": background_id}

    # ── 씬-배경 연결 ─────────────────────────────────────────

    def connect_scene_background(
        self, story_id: str, scene_id: str, background_id: str
    ) -> dict:
        story, scene = self._find_story_scene(story_id, scene_id)

        if self._background_repo.get(background_id) is None:
            raise BackgroundNotFoundError()

        scene["backgroundId"] = background_id
        self._story_repo.save_story(story)
        return {
            "storyId": story_id,
            "sceneId": scene_id,
            "backgroundId": background_id,
        }

    # ── 내부 헬퍼 ────────────────────────────────────────────

    def _find_scene(self, story_id: str, scene_id: str) -> dict:
        return self._find_story_scene(story_id, scene_id)[1]

    def _find_story_scene(self, story_id: str, scene_id: str) -> tuple[dict, dict]:
        story = self._story_repo.get(story_id)
        if story is None:
            raise StoryNotFoundError()
        for scene in story.get("scenes", []):
            if scene.get("sceneId") == scene_id:
                return story, scene
        raise SceneNotFoundError()


background_service = BackgroundService(
    story_repository,
    background_repository,
)

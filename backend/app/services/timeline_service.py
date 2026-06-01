"""타임라인 비즈니스 로직.

- story 단위로 scene order/duration 을 조회/저장한다.
- 멀티트랙 편집기가 아니라 스토리보드 기반(순서 재정렬 + duration 조절)이다.
- Voice/TTS, ffmpeg 렌더링은 이번 범위 아님. render plan 은 "2차 ffmpeg 가 그대로 쓸 데이터"까지만 만든다.
"""

from ..core.exceptions import (
    SceneNotFoundError,
    StoryNotFoundError,
    TimelineValidationError,
)
from ..repositories.background_repository import background_repository
from ..repositories.character_repo import character_repository
from ..repositories.story_repo import story_repository

DEFAULT_DURATION = 3.0
_TEXT_PREVIEW_MAX = 80


def _duration_of(scene: dict) -> float:
    """duration 이 없거나 비정상이면 기본값(3.0)으로 보정해 읽는다."""
    d = scene.get("duration")
    return float(d) if isinstance(d, (int, float)) and d > 0 else DEFAULT_DURATION


def _text_preview(scene: dict) -> str:
    """타임라인 카드용 짧은 문장: 첫 narration → 없으면 첫 dialogue → 없으면 ''. 80자 컷."""
    items = scene.get("items") or []
    narration = next((i for i in items if i.get("type") == "narration" and i.get("text")), None)
    chosen = narration or next((i for i in items if i.get("text")), None)
    text = (chosen or {}).get("text", "") or ""
    return text[:_TEXT_PREVIEW_MAX]


def _ready_status(scene: dict) -> dict:
    items = scene.get("items") or []
    return {
        "hasBackground": scene.get("backgroundId") is not None,
        "hasCharacters": len(scene.get("characters") or []) > 0,
        "hasText": any((i.get("text") or "").strip() for i in items),
    }


class TimelineService:
    def __init__(self, story_repo, background_repo, character_repo):
        self._story_repo = story_repo
        self._background_repo = background_repo
        self._character_repo = character_repo

    def _get_story_or_404(self, story_id: str) -> dict:
        story = self._story_repo.get(story_id)
        if story is None:
            raise StoryNotFoundError()
        return story

    def _sorted_scenes(self, story: dict) -> list[dict]:
        return sorted(story.get("scenes", []), key=lambda s: s.get("order", 0))

    def _background_summary(self, scene: dict) -> dict | None:
        bg_id = scene.get("backgroundId")
        if not bg_id:
            return None
        bg = self._background_repo.get(bg_id)
        return {"backgroundId": bg_id, "imageUrl": (bg or {}).get("imageUrl")}

    def _character_summaries(self, scene: dict) -> list[dict]:
        result = []
        for ch in scene.get("characters") or []:
            char = self._character_repo.get(ch.get("characterId"))
            if char is None:
                continue  # 라이브러리에서 삭제된 캐릭터는 타임라인 요약에서 제외
            result.append(
                {
                    "characterId": char.get("characterId"),
                    "name": char.get("name"),
                    "imageUrl": char.get("imageUrl"),
                    "layout": ch.get("layout"),  # 합성 미리보기용 배치(씬-캐릭터 항목에 저장됨)
                }
            )
        return result

    def _scene_response(self, scene: dict) -> dict:
        return {
            "sceneId": scene.get("sceneId"),
            "order": scene.get("order"),
            "duration": _duration_of(scene),
            "textPreview": _text_preview(scene),
            "background": self._background_summary(scene),
            "characters": self._character_summaries(scene),
            "readyStatus": _ready_status(scene),
        }

    # ── 조회 ──────────────────────────────────────────────
    def get_timeline(self, story_id: str) -> dict:
        story = self._get_story_or_404(story_id)
        scenes = [self._scene_response(s) for s in self._sorted_scenes(story)]
        total = round(sum(s["duration"] for s in scenes), 3)
        return {"storyId": story_id, "totalDuration": total, "scenes": scenes}

    # ── 저장 ──────────────────────────────────────────────
    def update_timeline(self, story_id: str, scene_updates: list) -> dict:
        """전체 scene 목록을 받아 각 scene 의 재생 길이(duration)를 저장한다.

        - 순서(order)는 스토리 원본 그대로 유지한다(타임라인은 재배치하지 않음).
        - 요청은 story 의 모든 scene 을 정확히 한 번씩 포함해야 한다(누락/초과/중복 → 400).
        - 존재하지 않는 sceneId → 404. duration 범위는 Pydantic Field(422)에서 막힘.
        """
        story = self._get_story_or_404(story_id)
        story_scenes = {s.get("sceneId"): s for s in story.get("scenes", [])}

        req_ids = [su.sceneId for su in scene_updates]
        # 존재하지 않는 sceneId
        for sid in req_ids:
            if sid not in story_scenes:
                raise SceneNotFoundError()
        # 전체 목록 정확히 1번씩 (중복/누락/초과 방지)
        if len(req_ids) != len(set(req_ids)) or set(req_ids) != set(story_scenes.keys()):
            raise TimelineValidationError()

        # duration 만 저장 (in-memory dict 직접 갱신 → dev_persist 로 유지). order 는 건드리지 않음.
        for su in scene_updates:
            story_scenes[su.sceneId]["duration"] = float(su.duration)

        return self.get_timeline(story_id)

    # ── render plan (2차 ffmpeg 입력용 데이터 — 실제 렌더/파일생성 안 함) ──
    def build_render_plan(self, story_id: str) -> dict:
        story = self._get_story_or_404(story_id)
        scenes = []
        for scene in self._sorted_scenes(story):
            bg = self._background_repo.get(scene.get("backgroundId")) if scene.get("backgroundId") else None
            characters = []
            for ch in scene.get("characters") or []:
                char = self._character_repo.get(ch.get("characterId"))
                if char is None:
                    continue
                characters.append(
                    {
                        "characterId": char.get("characterId"),
                        "name": char.get("name"),
                        "imageUrl": char.get("imageUrl"),
                        "layout": ch.get("layout"),  # x/y/scale/rotation/zIndex/flipX (없으면 None)
                    }
                )
            subtitles = [
                {
                    "order": idx,
                    "type": it.get("type"),
                    "speaker": it.get("speaker"),
                    "text": it.get("text"),
                    "emotion": it.get("emotion"),
                    "emotionLabel": it.get("emotionLabel"),
                }
                for idx, it in enumerate(scene.get("items") or [], start=1)
            ]
            scenes.append(
                {
                    "sceneId": scene.get("sceneId"),
                    "order": scene.get("order"),
                    "duration": _duration_of(scene),
                    "backgroundImageUrl": (bg or {}).get("imageUrl"),
                    "characters": characters,
                    "subtitles": subtitles,
                }
            )
        total = round(sum(s["duration"] for s in scenes), 3)
        return {"storyId": story_id, "totalDuration": total, "scenes": scenes}


timeline_service = TimelineService(story_repository, background_repository, character_repository)

"""자막(텍스트 오버레이) 비즈니스 로직.

자막은 스토리 대본(`scene.items`)에서 **줄당 1개 자동 생성**된다.
- 씬 편집에서 자막 추가/텍스트 변경은 없다. 사용자는 **cue 그룹 배정 + 위치/크기/회전(layout)** 만 바꾼다.
- 줄별 설정은 `scene.subtitleSettings = { "item index": {cueOrder, layout} }` 에 저장된다. 텍스트는 항상 items에서(읽기전용).
- 기본 cueOrder = item 순번+1 (각 줄이 자기 cue 그룹). 사용자가 다른 줄을 기존 cue 그룹에 묶을 수 있다.
- cue 그룹 번호는 고정 — 이동/재부여 없음. 같은 cueOrder에 독립 자막 여러 개 가능. /timeline 이 cue 그룹 단위로 타이밍.
"""

from ..core.exceptions import SceneNotFoundError, StoryNotFoundError
from ..repositories.story_repo import story_repository

_DEFAULT_X = 0.5
_DEFAULT_WIDTH = 0.75
_DEFAULT_FONT = 0.06


def _default_layout(index: int) -> dict:
    """줄이 여러 개면 하단에서 위로 살짝 쌓아 겹침을 줄인다."""
    return {
        "x": _DEFAULT_X,
        "y": max(0.4, round(0.86 - index * 0.1, 3)),
        "width": _DEFAULT_WIDTH,
        "fontSize": _DEFAULT_FONT,
        "rotation": 0,
        "zIndex": 100,
        "align": "center",
    }


def build_text_overlays(scene: dict) -> list[dict]:
    """items + 저장된 subtitleSettings 로 자막 목록 조립(읽기전용 파생).

    - textOverlayId/sourceItemIndex 는 item 순번에 고정 → TTS 등과 안정 매핑.
    - cueOrder 기본값 = item 순번+1. 저장된 설정이 있으면 그 cueOrder/layout 사용.
    - cueOrder, 그다음 sourceItemIndex 순으로 정렬(그룹별로 모이게).
    """
    items = scene.get("items") or []
    settings = scene.get("subtitleSettings") or {}
    scene_id = scene.get("sceneId")
    result = []
    for i, it in enumerate(items):
        text = (it.get("text") or "").strip()
        if not text:
            continue
        s = settings.get(str(i)) or settings.get(i) or {}
        result.append(
            {
                "textOverlayId": f"{scene_id}_t{i}",
                "sourceItemIndex": i,
                "cueOrder": s.get("cueOrder") if isinstance(s.get("cueOrder"), int) and s.get("cueOrder") >= 1 else i + 1,
                "type": it.get("type") or "narration",
                "speaker": it.get("speaker"),
                "text": text,
                "layout": s.get("layout") or _default_layout(i),
                "style": None,
            }
        )
    result.sort(key=lambda o: (o["cueOrder"], o["sourceItemIndex"]))
    return result


class TextOverlayService:
    def __init__(self, story_repo):
        self._story_repo = story_repo

    def _find_scene(self, story_id: str, scene_id: str) -> dict:
        story = self._story_repo.get(story_id)
        if story is None:
            raise StoryNotFoundError()
        for scene in story.get("scenes", []):
            if scene.get("sceneId") == scene_id:
                return scene
        raise SceneNotFoundError()

    def update_subtitles(self, story_id: str, scene_id: str, overlays: list) -> dict:
        """자막 줄별 설정(cueOrder+layout)만 저장한다(전체 교체). 텍스트/추가/삭제는 없음.

        overlays: [{itemIndex, cueOrder, layout}] — itemIndex 는 items 범위 안만 반영.
        반환: items + 저장 설정으로 조립한 자막 목록.
        """
        scene = self._find_scene(story_id, scene_id)
        item_count = len(scene.get("items") or [])
        scene["subtitleSettings"] = {
            str(o.itemIndex): {"cueOrder": o.cueOrder, "layout": o.layout.model_dump()}
            for o in overlays
            if 0 <= o.itemIndex < item_count
        }
        return {
            "storyId": story_id,
            "sceneId": scene_id,
            "textOverlays": build_text_overlays(scene),
        }


text_overlay_service = TextOverlayService(story_repository)

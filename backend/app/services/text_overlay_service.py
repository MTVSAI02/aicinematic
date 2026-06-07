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

# 자막 배경 박스 불투명도(고정). 추후 사용자 조절 기능 추가 시 이 상수만 분리/대체.
SUBTITLE_BACKGROUND_OPACITY = 0.3
# subtitleBackground(none/black/white) → style.backgroundColor 변환. none/미선택이면 미포함.
_SUBTITLE_BACKGROUND_COLORS = {
    "black": f"rgba(0, 0, 0, {SUBTITLE_BACKGROUND_OPACITY})",
    "white": f"rgba(255, 255, 255, {SUBTITLE_BACKGROUND_OPACITY})",
}


def _display_text(item_type: str, text: str) -> str:
    """표시용 자막 텍스트. dialogue 면 "..." 로 감싼다(나레이션은 그대로).

    - 원본 item.text 는 수정하지 않는다 — 파생되는 overlay text 에만 적용(표시/렌더 전용).
    - 이미 큰따옴표로 시작·끝나면 중복으로 붙이지 않는다.
    """
    if item_type == "dialogue" and not (text.startswith('"') and text.endswith('"')):
        return f'"{text}"'
    return text


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
    # 글자색은 씬 단위(sceneTextColor). 미선택이면 기본 검정(#111111) — 모든 자막 style.color 동일.
    scene_color = scene.get("sceneTextColor") or "#111111"
    # 자막 배경 박스도 씬 단위(subtitleBackground: none/black/white). none/미선택이면 backgroundColor 미포함.
    scene_bg = _SUBTITLE_BACKGROUND_COLORS.get(scene.get("subtitleBackground"))
    result = []
    for i, it in enumerate(items):
        text = (it.get("text") or "").strip()
        if not text:
            continue
        s = settings.get(str(i)) or settings.get(i) or {}
        item_type = it.get("type") or "narration"
        result.append(
            {
                "textOverlayId": f"{scene_id}_t{i}",
                "sourceItemIndex": i,
                "cueOrder": s.get("cueOrder") if isinstance(s.get("cueOrder"), int) and s.get("cueOrder") >= 1 else i + 1,
                "type": item_type,
                "speaker": it.get("speaker"),
                "text": _display_text(item_type, text),  # dialogue → "..." (표시용, 원본 미수정)
                "layout": s.get("layout") or _default_layout(i),
                # 모든 자막에 씬 글자색/배경 동일 적용. 타임라인/렌더/씬편집이 style.color·backgroundColor 읽음.
                # backgroundColor 는 있을 때만 넣어, none 이면 기존처럼 투명(키 자체 없음).
                "style": (
                    {"color": scene_color, "backgroundColor": scene_bg}
                    if scene_bg
                    else {"color": scene_color}
                ),
            }
        )
    result.sort(key=lambda o: (o["cueOrder"], o["sourceItemIndex"]))
    return result


class TextOverlayService:
    def __init__(self, story_repo):
        self._story_repo = story_repo

    def _find_story_scene(self, story_id: str, scene_id: str) -> tuple[dict, dict]:
        story = self._story_repo.get(story_id)
        if story is None:
            raise StoryNotFoundError()
        for scene in story.get("scenes", []):
            if scene.get("sceneId") == scene_id:
                return story, scene
        raise SceneNotFoundError()

    def update_subtitles(
        self,
        story_id: str,
        scene_id: str,
        overlays: list,
        scene_text_color: str | None = None,
        subtitle_background: str | None = None,
    ) -> dict:
        """자막 줄별 설정(cueOrder+layout) + 씬 글자색/배경을 저장한다(전체 교체).

        overlays: [{itemIndex, cueOrder, layout}] — itemIndex 는 items 범위 안만 반영.
        scene_text_color: 씬 전체 자막 글자색(None 이면 자동 색).
        subtitle_background: 씬 전체 자막 배경(none/black/white, None 이면 none). 반환: 조립한 자막 목록.
        """
        story, scene = self._find_story_scene(story_id, scene_id)
        item_count = len(scene.get("items") or [])
        scene["sceneTextColor"] = scene_text_color  # 씬 단위 글자색(None=자동)
        scene["subtitleBackground"] = subtitle_background  # 씬 단위 배경(None/none=투명)
        scene["subtitleSettings"] = {
            str(o.itemIndex): {
                "cueOrder": o.cueOrder,
                "layout": o.layout.model_dump(),
            }
            for o in overlays
            if 0 <= o.itemIndex < item_count
        }
        self._story_repo.save_story(story)
        return {
            "storyId": story_id,
            "sceneId": scene_id,
            "textOverlays": build_text_overlays(scene),
        }


text_overlay_service = TextOverlayService(story_repository)

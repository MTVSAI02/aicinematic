"""자막(텍스트 오버레이) 스키마.

자막은 scene.items(대본)에서 **줄당 1개 자동 파생**된다(텍스트 읽기전용, 별도 복사 안 함).
- 저장하는 값은 줄별 {cueOrder, layout}뿐(scene.subtitleSettings). 텍스트/speaker/type은 항상 items에서 읽는다.
- layout은 캐릭터와 같은 **정규화(0~1)** 좌표계 → /scene-editor, /timeline 썸네일, 2차 ffmpeg 렌더가
  해상도가 달라도 같은 위치/크기로 재현한다.
필드명은 프로젝트 공통 규칙대로 camelCase 직접 사용.
"""

from typing import Literal

from pydantic import BaseModel, Field


class TextOverlayLayout(BaseModel):
    """자막 배치 정보(정규화). x/y는 박스 중심, width/fontSize는 스테이지 비율."""

    x: float = Field(default=0.5, ge=0.0, le=1.0)  # 중심 x (스테이지 너비 기준)
    y: float = Field(default=0.86, ge=0.0, le=1.0)  # 중심 y (스테이지 높이 기준)
    width: float = Field(default=0.75, ge=0.1, le=1.0)  # 텍스트 박스 폭(스테이지 너비 대비)
    fontSize: float = Field(default=0.06, ge=0.01, le=0.2)  # 글자 크기(스테이지 높이 대비)
    rotation: float = Field(default=0.0, ge=-360.0, le=360.0)  # 각도(도)
    zIndex: int = Field(default=100, ge=0, le=999)  # 텍스트는 캐릭터 위 → 기본 100대
    align: Literal["left", "center", "right"] = "center"


class TextOverlayStyle(BaseModel):
    """자막 스타일. 1차에서는 가독성용 기본값만 쓰고 편집 UI는 2차.

    borderRadius/padding은 스테이지 높이 대비 정규화 값(렌더 해상도 독립).
    """

    color: str = "#ffffff"
    backgroundColor: str = "rgba(0,0,0,0.45)"
    fontWeight: str = "600"
    borderRadius: float = Field(default=0.02, ge=0.0, le=0.5)
    padding: float = Field(default=0.02, ge=0.0, le=0.5)


class TextOverlay(BaseModel):
    """씬 위에 배치된 자막 1개. (items 1줄에서 파생, 텍스트 읽기전용)"""

    textOverlayId: str = Field(min_length=1)
    sourceItemIndex: int = Field(ge=0)  # 이 자막의 출처 대본 줄(고정)
    cueOrder: int = Field(default=1, ge=1)  # 속한 cue 그룹 번호(같은 cue에 자막 여러 개 가능)
    type: str = "narration"  # narration | dialogue
    speaker: str | None = None
    text: str = Field(min_length=1)  # items[sourceItemIndex].text (읽기전용)
    layout: TextOverlayLayout = Field(default_factory=TextOverlayLayout)
    style: TextOverlayStyle | None = None


class SceneSubtitleSetting(BaseModel):
    """PATCH 요청의 자막 1개. itemIndex = 대본 줄 번호(자막은 줄당 1개)."""

    itemIndex: int = Field(ge=0)
    cueOrder: int = Field(ge=1)
    layout: TextOverlayLayout


class SceneSubtitleSettingsRequest(BaseModel):
    """PATCH /api/scenes/{sceneId}/subtitles body.

    자막은 대본(items)에서 자동 생성 → **추가/텍스트 변경 없음**. 저장하는 건 줄별 **cueOrder(그룹) + layout**뿐.
    전체 교체. itemIndex 가 items 범위를 벗어나면 무시한다.
    """

    storyId: str
    overlays: list[SceneSubtitleSetting] = []


class SceneTextOverlaysResponse(BaseModel):
    storyId: str
    sceneId: str
    textOverlays: list[TextOverlay] = []  # items + 저장된 cueOrder/layout 으로 조립한 결과

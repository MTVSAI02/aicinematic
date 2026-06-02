"""타임라인 API 스키마.

타임라인은 story 단위로 scene 재생 길이(duration)를 관리한다.
순서(order)는 스토리 원본 그대로 고정 — 타임라인에서 재배치하지 않는다.
필드명은 프로젝트 공통 규칙대로 camelCase 직접 사용(snake_case+alias 안 씀).
"""

from pydantic import BaseModel, ConfigDict, Field

from .character import SceneCharacterLayout
from .text_overlay import TextOverlay


# ── PATCH 요청 ──────────────────────────────────────────────
class TimelineSceneUpdate(BaseModel):
    """타임라인 저장 요청의 scene 1개. 재생 길이(duration)만 저장한다(순서 변경 없음)."""

    sceneId: str = Field(min_length=1)
    duration: float = Field(ge=1.0, le=30.0)


class TimelineUpdateRequest(BaseModel):
    # 전체 scene 목록을 요구한다(부분 업데이트 금지). 비어 있으면 422.
    scenes: list[TimelineSceneUpdate] = Field(min_length=1)


# ── 조회 응답 ──────────────────────────────────────────────
class TimelineBackgroundSummary(BaseModel):
    backgroundId: str
    imageUrl: str | None = None


class TimelineCharacterSummary(BaseModel):
    characterId: str
    name: str
    imageUrl: str | None = None
    layout: SceneCharacterLayout | None = None  # 합성 미리보기용 배치(x/y/scale/rotation/zIndex/flipX)


class TimelineReadyStatus(BaseModel):
    hasBackground: bool
    hasCharacters: bool
    hasText: bool
    # hasAudio 는 이번 범위 아님(추후 TTS 붙으면 확장). 1차에선 내려보내지 않는다.


class TimelineSceneResponse(BaseModel):
    sceneId: str
    order: int  # 스토리 원본 순서. 타임라인에서 변경하지 않는다.
    duration: float
    textPreview: str
    background: TimelineBackgroundSummary | None = None
    characters: list[TimelineCharacterSummary] = []
    textOverlays: list[TextOverlay] = []  # 타임라인 합성 미리보기에서 자막까지 재현
    readyStatus: TimelineReadyStatus


class TimelineResponse(BaseModel):
    storyId: str
    totalDuration: float
    scenes: list[TimelineSceneResponse]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "storyId": "story_mock_001",
                "totalDuration": 10.5,
                "scenes": [
                    {
                        "sceneId": "scene_001",
                        "order": 1,
                        "duration": 3.0,
                        "textPreview": "어린왕자는 작은 별 위에 앉아 노을을 바라보고 있었다.",
                        "background": {"backgroundId": "bg_mock_001", "imageUrl": "/storage/backgrounds/library/bg_mock_001.png"},
                        "characters": [{"characterId": "char_mock_001", "name": "어린왕자", "imageUrl": "/storage/characters/char_mock_001.png"}],
                        "readyStatus": {"hasBackground": True, "hasCharacters": True, "hasText": True},
                    }
                ],
            }
        }
    )


# ── render plan (2차 ffmpeg 렌더가 그대로 사용할 구조) ─────────
class RenderPlanCharacter(BaseModel):
    characterId: str
    name: str | None = None
    imageUrl: str | None = None  # 포즈 적용 시 포즈 이미지, 아니면 원본
    poseId: str | None = None  # 적용된 포즈(없으면 None=원본)
    layout: SceneCharacterLayout | None = None  # x/y/scale/rotation/zIndex/flipX (없으면 None)


class RenderPlanSubtitle(BaseModel):
    order: int
    type: str | None = None  # narration | dialogue 등
    speaker: str | None = None
    text: str | None = None
    emotion: str | None = None
    emotionLabel: str | None = None


class RenderPlanScene(BaseModel):
    sceneId: str
    order: int
    duration: float
    backgroundImageUrl: str | None = None
    characters: list[RenderPlanCharacter] = []
    subtitles: list[RenderPlanSubtitle] = []  # 원본 대본 라인(타이밍/자막 텍스트 출처)
    textOverlays: list[TextOverlay] = []  # 사용자가 배치한 자막 레이어(2차 ffmpeg가 좌표대로 그림)


class RenderPlanResponse(BaseModel):
    storyId: str
    totalDuration: float
    scenes: list[RenderPlanScene]

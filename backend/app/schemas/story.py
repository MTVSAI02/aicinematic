from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .character import SceneCharacterItem
from .text_overlay import TextOverlay


def _not_blank(value: str) -> str:
    if not (value or "").strip():
        raise ValueError("must not be blank")
    return value


class StructuredStoryItem(BaseModel):
    """structured 입력의 item 한 줄(나레이션/대사). 사용자는 문법/따옴표를 입력하지 않는다."""

    emotion: str | None = Field(default=None, description="감정 코드(없으면 emotionLabel 로 서버가 파생)")
    emotionLabel: str = Field(description="셀렉터에서 고른 한글 라벨(예: 잔잔함)")
    speaker: str | None = Field(default=None, description="비어 있으면 narration, 있으면 dialogue")
    text: str = Field(description="나레이션 또는 대사 본문")

    @field_validator("emotionLabel", "text")
    @classmethod
    def _nb(cls, v: str) -> str:
        return _not_blank(v)


class StructuredScene(BaseModel):
    sceneOrder: int = Field(ge=1, description="씬 순서(서버에서 1..N 으로 재정렬)")
    items: list[StructuredStoryItem] = Field(min_length=1, description="씬당 최소 1개")


class StoryParseRequest(BaseModel):
    """대본 입력. inputMode=raw(기존 textarea) / structured(씬·item 구조화) 둘 다 지원."""

    title: str = Field(min_length=1, examples=["어린 왕자"])
    inputMode: Literal["raw", "structured"] = Field(default="raw", description="기본 raw(하위호환)")
    script: str | None = Field(
        default=None,
        description="raw 모드 본문. 줄 맨 앞에 선택적 [감정] 태그. 예: [화남] 어린왕자: \"싫어\"",
        examples=["[잔잔함] 어린 왕자는 조용히 별을 바라보았다.\n여우: \"안녕, 나는 여우야.\""],
    )
    scenes: list[StructuredScene] | None = Field(default=None, description="structured 모드 씬 목록")

    @field_validator("title")
    @classmethod
    def _title_nb(cls, v: str) -> str:
        return _not_blank(v)

    @model_validator(mode="after")
    def _check_mode(self):
        if self.inputMode == "structured":
            if not self.scenes:
                raise ValueError("structured 모드는 scenes 가 1개 이상 필요합니다.")
        elif not (self.script or "").strip():
            raise ValueError("raw 모드는 script 가 필요합니다.")
        return self


class EmotionOption(BaseModel):
    """GET /api/stories/emotions 응답 한 항목. label 유일, value 는 중복 가능."""

    label: str = Field(examples=["기쁨"])
    value: str = Field(examples=["happy"])


class StoryItemResponse(BaseModel):
    type: str = Field(description="narration 또는 dialogue")
    speaker: str | None = Field(description="dialogue일 때 화자명, narration이면 null")
    text: str
    emotion: str = Field(description="감정 키 (neutral/calm/happy/sad/angry/scared/excited/friendly/serious)")
    emotionLabel: str = Field(description="감정 한글 라벨 (기본/잔잔함/기쁨/슬픔/화남/무서움/신남/다정함/진지함)")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"type": "narration", "speaker": None, "text": "어린 왕자는 조용히 별을 바라보았다.", "emotion": "calm", "emotionLabel": "잔잔함"},
                {"type": "dialogue", "speaker": "어린왕자", "text": "싫어", "emotion": "angry", "emotionLabel": "화남"},
            ]
        }
    )


class SceneResponse(BaseModel):
    sceneId: str = Field(description="scene_001, scene_002 형식으로 자동 생성")
    order: int = Field(description="1부터 순서대로 부여")
    duration: float = Field(default=3.0, description="타임라인 재생 길이(초). 기본 3.0, 1.0~30.0")
    backgroundId: str | None = Field(
        default=None, description="연결된 배경 ID. 없으면 null (PATCH /api/scenes/{sceneId}/background로 연결)"
    )
    characters: list[SceneCharacterItem] = Field(
        default_factory=list,
        description="연결된 캐릭터 목록(씬당 다중). PATCH /api/scenes/{sceneId}/character로 추가/수정, DELETE로 개별 제거. 각 항목에 sceneAppearancePrompt(표정/포즈) 포함",
    )
    items: list[StoryItemResponse]
    # 자막은 items(대본 줄)에서 줄당 1개 자동 생성. 백엔드가 조립한 결과를 그대로 내려준다(단일 소스).
    # 프론트는 이 목록을 렌더하고, 변경(cueOrder/layout)만 PATCH /api/scenes/{sceneId}/subtitles 로 보낸다.
    textOverlays: list[TextOverlay] = Field(default_factory=list)


class StoryParseResponse(BaseModel):
    storyId: str = Field(description="story_mock_001 형식으로 자동 생성")
    title: str
    narratorVoiceId: str | None = Field(
        default=None,
        description="나레이션 보이스 ID. 없으면 null (PATCH /api/stories/{storyId}/narrator-voice로 연결)",
    )
    scenes: list[SceneResponse]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "storyId": "story_mock_001",
                "title": "어린 왕자",
                "narratorVoiceId": None,
                "scenes": [
                    {
                        "sceneId": "scene_001",
                        "order": 1,
                        "backgroundId": None,
                        "items": [
                            {"type": "narration", "speaker": None, "text": "어린 왕자는 작은 별에 혼자 살았어요.", "emotion": "calm", "emotionLabel": "잔잔함"},
                            {"type": "dialogue", "speaker": "어린왕자", "text": "오늘은 어디로 여행을 떠나볼까?", "emotion": "neutral", "emotionLabel": "기본"},
                        ],
                    },
                    {
                        "sceneId": "scene_002",
                        "order": 2,
                        "backgroundId": None,
                        "items": [
                            {"type": "narration", "speaker": None, "text": "어린 왕자는 별빛을 따라 사막에 도착했어요.", "emotion": "calm", "emotionLabel": "잔잔함"},
                            {"type": "dialogue", "speaker": "여우", "text": "안녕, 나는 여우야.", "emotion": "neutral", "emotionLabel": "기본"},
                        ],
                    },
                ],
            }
        }
    )


class NarratorVoiceUpdateRequest(BaseModel):
    """나레이션 보이스 연결/해제 요청.

    voiceId가 있으면 그 보이스로 연결하고, null이면 연결을 해제한다.
    (캐릭터 보이스 연결 PATCH /api/characters/{id}/voice 와 동일한 정책)
    """

    voiceId: str | None = Field(
        default=None, description="연결할 보이스 ID. null이면 나레이션 보이스 해제"
    )


class NarratorVoiceResponse(BaseModel):
    storyId: str
    narratorVoiceId: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"storyId": "story_mock_001", "narratorVoiceId": "voice_mock_002"}
        }
    )


class VoiceLockItem(BaseModel):
    """대상(나레이션/캐릭터) 하나의 연결·잠금 상태."""

    targetType: str = Field(description="narration 또는 character")
    targetId: str = Field(description='"narration" 또는 characterId (미매칭 speaker면 speaker명)')
    displayName: str = Field(description="나레이션 또는 캐릭터/화자 이름")
    imageUrl: str | None = Field(default=None, description="캐릭터 썸네일 (나레이션/미매칭이면 null)")
    matched: bool = Field(description="등장 speaker가 저장된 캐릭터와 매칭됐는지 (false면 잠금 불가)")
    voiceId: str | None = Field(default=None, description="연결된 보이스 ID (없으면 null)")
    voiceName: str | None = Field(default=None, description="연결된 보이스 이름")
    lockStatus: str = Field(description="unlocked / locked")
    ttsStatus: str = Field(description="idle / generating / ready / failed / stale")
    reason: str | None = Field(default=None, description="잠금 불가 사유(예: character_not_found)")


class VoiceLocksResponse(BaseModel):
    """GET /voice-locks — 대상별 잠금 상태 + 다음 단계 이동 가능 여부."""

    storyId: str
    allLocked: bool = Field(description="모든 필수 대상이 locked 인지")
    nextStepEnabled: bool = Field(
        description="다음 단계 이동 가능 (= 모든 대상 locked + 실패 대상 없음). generating 은 허용, failed 는 차단"
    )
    hasFailed: bool = Field(default=False, description="음성 생성 실패(ttsStatus=failed) 대상이 하나라도 있는지")
    voiceLocks: list[VoiceLockItem] = Field(default_factory=list)


class VoiceLockActionResponse(BaseModel):
    """POST /voice-locks/{targetType}/{targetId}/lock · /unlock — 해당 대상 상태 + 전체 게이팅."""

    storyId: str
    targetType: str
    targetId: str
    lockStatus: str = Field(description="unlocked / locked")
    ttsStatus: str = Field(description="idle / generating / ready / failed / stale")
    allLocked: bool
    nextStepEnabled: bool

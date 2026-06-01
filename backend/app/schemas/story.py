from pydantic import BaseModel, ConfigDict, Field

from .character import SceneCharacterItem


class StoryParseRequest(BaseModel):
    title: str = Field(examples=["어린 왕자"])
    script: str = Field(
        description="줄 맨 앞에 선택적으로 [감정] 태그를 붙일 수 있다. 예: [화남] 어린왕자: \"싫어\"",
        examples=[
            "[잔잔함] 어린 왕자는 조용히 별을 바라보았다.\n[화남] 어린왕자: \"싫어\"\n\n어린 왕자는 별빛을 따라 사막에 도착했어요.\n여우: \"안녕, 나는 여우야.\""
        ],
    )


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

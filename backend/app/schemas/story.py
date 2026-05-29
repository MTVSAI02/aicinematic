from pydantic import BaseModel, ConfigDict, Field


class StoryParseRequest(BaseModel):
    title: str = Field(examples=["어린 왕자"])
    script: str = Field(
        examples=[
            "어린 왕자는 작은 별에 혼자 살았어요.\n어린왕자: \"오늘은 어디로 여행을 떠나볼까?\"\n\n어린 왕자는 별빛을 따라 사막에 도착했어요.\n여우: \"안녕, 나는 여우야.\""
        ]
    )


class StoryItemResponse(BaseModel):
    type: str = Field(description="narration 또는 dialogue")
    speaker: str | None = Field(description="dialogue일 때 화자명, narration이면 null")
    text: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"type": "narration", "speaker": None, "text": "어린 왕자는 작은 별에 혼자 살았어요."},
                {"type": "dialogue", "speaker": "어린왕자", "text": "오늘은 어디로 여행을 떠나볼까?"},
            ]
        }
    )


class SceneResponse(BaseModel):
    sceneId: str = Field(description="scene_001, scene_002 형식으로 자동 생성")
    order: int = Field(description="1부터 순서대로 부여")
    items: list[StoryItemResponse]


class StoryParseResponse(BaseModel):
    storyId: str = Field(description="story_mock_001 형식으로 자동 생성")
    title: str
    scenes: list[SceneResponse]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "storyId": "story_mock_001",
                "title": "어린 왕자",
                "scenes": [
                    {
                        "sceneId": "scene_001",
                        "order": 1,
                        "items": [
                            {"type": "narration", "speaker": None, "text": "어린 왕자는 작은 별에 혼자 살았어요."},
                            {"type": "dialogue", "speaker": "어린왕자", "text": "오늘은 어디로 여행을 떠나볼까?"},
                        ],
                    },
                    {
                        "sceneId": "scene_002",
                        "order": 2,
                        "items": [
                            {"type": "narration", "speaker": None, "text": "어린 왕자는 별빛을 따라 사막에 도착했어요."},
                            {"type": "dialogue", "speaker": "여우", "text": "안녕, 나는 여우야."},
                        ],
                    },
                ],
            }
        }
    )

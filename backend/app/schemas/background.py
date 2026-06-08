from pydantic import BaseModel, ConfigDict, Field, field_validator


def _not_blank(value: str) -> str:
    """공백만으로 이루어진 문자열을 거부한다."""
    if not value.strip():
        raise ValueError("must not be blank")
    return value


# ── 프롬프트 추천 ─────────────────────────────────────────────


class BackgroundPromptSuggestionRequest(BaseModel):
    storyId: str
    sceneId: str


class BackgroundPromptSuggestionResponse(BaseModel):
    storyId: str
    sceneId: str
    sourceText: str
    suggestedPrompt: str
    finalPrompt: str


# ── 배경 생성 Job ─────────────────────────────────────────────


class BackgroundGenerateRequest(BaseModel):
    # 프론트는 제목(name) + prompt 를 보낸다. negativePrompt 는 받지 않음(AI 서버/워크플로 내부 고정값).
    # name: 라이브러리·씬편집에 표시될 배경 제목(사용자 입력, 필수).
    name: str = Field(min_length=1, examples=["별빛 사막"])
    prompt: str = Field(min_length=1, examples=["별빛이 비치는 조용한 사막, 따뜻한 동화풍 배경"])

    @field_validator("name", "prompt")
    @classmethod
    def not_blank(cls, value: str) -> str:
        return _not_blank(value)


# ── 배경 라이브러리 ───────────────────────────────────────────


class BackgroundResponse(BaseModel):
    backgroundId: str
    name: str
    prompt: str
    finalPrompt: str
    imageUrl: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "backgroundId": "bg_mock_001",
                "name": "별빛 사막 배경",
                "prompt": "별빛이 비치는 조용한 사막, 따뜻한 동화풍 배경",
                "finalPrompt": "별빛이 비치는 조용한 사막, 따뜻한 동화풍 배경, storybook background, soft painterly style, clean composition, background only, no characters",
                "imageUrl": None,
            }
        }
    )


class BackgroundUpdateRequest(BaseModel):
    # MVP에서는 name만 수정 가능. (prompt/finalPrompt/imageUrl 은 생성 결과 추적용이라 수정 불가)
    name: str | None = Field(default=None, min_length=1)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _not_blank(value)


class BackgroundDeleteResponse(BaseModel):
    deleted: bool
    backgroundId: str


# ── 씬-배경 연결 ──────────────────────────────────────────────


class SceneBackgroundUpdateRequest(BaseModel):
    # PATCH /api/scenes/{sceneId}/background 의 body. storyId 를 함께 받는다.
    storyId: str
    backgroundId: str


class SceneBackgroundResponse(BaseModel):
    storyId: str
    sceneId: str
    backgroundId: str | None = None

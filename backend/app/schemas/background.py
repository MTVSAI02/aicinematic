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
    negativePrompt: str


# ── 후보 생성 Job ─────────────────────────────────────────────


class BackgroundGenerateRequest(BaseModel):
    # 후보 개수(count)는 요청으로 받지 않는다.
    # 몇 장을 생성할지는 ComfyUI 워크플로(배치 크기)가 결정하며, 백엔드는 그 결과를 그대로 전달한다.
    prompt: str = Field(min_length=1, examples=["별빛이 비치는 조용한 사막, 따뜻한 동화풍 배경"])
    negativePrompt: str | None = None

    @field_validator("prompt")
    @classmethod
    def prompt_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class BackgroundCandidate(BaseModel):
    candidateId: str
    prompt: str
    finalPrompt: str
    negativePrompt: str
    imageUrl: str | None = None


# ── 배경 라이브러리 ───────────────────────────────────────────


class BackgroundCreateRequest(BaseModel):
    candidateId: str
    name: str = Field(min_length=1, examples=["별빛 사막 배경"])

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class BackgroundResponse(BaseModel):
    backgroundId: str
    name: str
    prompt: str
    finalPrompt: str
    negativePrompt: str
    imageUrl: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "backgroundId": "bg_mock_001",
                "name": "별빛 사막 배경",
                "prompt": "별빛이 비치는 조용한 사막, 따뜻한 동화풍 배경",
                "finalPrompt": "별빛이 비치는 조용한 사막, 따뜻한 동화풍 배경, storybook background, soft painterly style, clean composition, background only, no characters",
                "negativePrompt": "characters, people, animals, text, watermark, blurry, low quality",
                "imageUrl": None,
            }
        }
    )


class BackgroundUpdateRequest(BaseModel):
    # MVP에서는 name만 수정 가능. (prompt/finalPrompt/negativePrompt/imageUrl 은 생성 결과 추적용이라 수정 불가)
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

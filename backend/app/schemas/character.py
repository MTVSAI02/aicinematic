from pydantic import BaseModel, ConfigDict, Field, field_validator


def _not_blank(value: str) -> str:
    """공백만으로 이루어진 문자열을 거부한다."""
    if not value.strip():
        raise ValueError("must not be blank")
    return value


class CharacterGenerateRequest(BaseModel):
    """캐릭터 생성(Job) 요청. 스타일/seed/reference는 ComfyUI 파트에서 관리하므로 받지 않는다."""

    name: str = Field(min_length=1, examples=["어린왕자"])
    appearancePrompt: str = Field(min_length=1, examples=["금발 단발, 초록 외투를 입은 작은 소년"])

    @field_validator("name", "appearancePrompt")
    @classmethod
    def not_blank(cls, value: str) -> str:
        return _not_blank(value)


class CharacterCreateRequest(BaseModel):
    """이미 만들어진 캐릭터 결과를 직접 저장하는 요청."""

    name: str = Field(min_length=1, examples=["어린왕자"])
    appearancePrompt: str = Field(min_length=1, examples=["금발 단발, 초록 외투를 입은 작은 소년"])
    imageUrl: str | None = Field(default=None, examples=[None])

    @field_validator("name", "appearancePrompt")
    @classmethod
    def not_blank(cls, value: str) -> str:
        return _not_blank(value)


class CharacterUpdateRequest(BaseModel):
    """캐릭터 부분 수정 요청. 전달된 필드만 반영한다."""

    name: str | None = Field(default=None, min_length=1, examples=["작은 왕자"])
    appearancePrompt: str | None = Field(default=None, min_length=1)
    imageUrl: str | None = Field(default=None, examples=["/static/characters/prince.png"])

    @field_validator("name", "appearancePrompt")
    @classmethod
    def not_blank(cls, value: str | None) -> str | None:
        # 전달된 경우에만 공백 문자열을 거부한다 (None은 "미전달"이므로 통과).
        if value is None:
            return value
        return _not_blank(value)


class CharacterVoiceUpdateRequest(BaseModel):
    # 캐릭터에 연결할 보이스(라이브러리)의 voiceId. null이면 연결 해제.
    voiceId: str | None = None


class CharacterResponse(BaseModel):
    characterId: str = Field(description="char_mock_001 형식으로 자동 생성")
    name: str
    appearancePrompt: str
    imageUrl: str | None = Field(default=None, description="생성된 이미지 경로. 없으면 null")
    voiceId: str | None = Field(default=None, description="연결된 보이스 ID. 없으면 null")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "characterId": "char_mock_001",
                "name": "어린왕자",
                "appearancePrompt": "금발 단발, 초록 외투를 입은 작은 소년",
                "imageUrl": None,
                "voiceId": None,
            }
        }
    )


class CharacterDeleteResponse(BaseModel):
    deleted: bool
    characterId: str


class CharacterGenerateJobResponse(BaseModel):
    jobId: str = Field(description="job_mock_001 형식으로 자동 생성")
    status: str = Field(description="생성 Job 상태")
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "jobId": "job_mock_001",
                "status": "completed",
                "message": "Character generation job completed with mock result.",
            }
        }
    )

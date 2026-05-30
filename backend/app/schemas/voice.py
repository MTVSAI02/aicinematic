from pydantic import BaseModel, ConfigDict, Field, field_validator


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank")
    return value


class VoiceCreateRequest(BaseModel):
    """보이스 자산 생성 요청.

    백엔드/사용자가 정하는 메타(name/description/voicePrompt)만 받는다.
    provider/model/sampleAudioUrl/status 같은 "실제 목소리를 어떻게 만드는가"는
    AI/TTS 파트(김도연)의 영역이라 생성 요청으로 받지 않는다.
    (캐릭터에서 seed/style/model을 백엔드가 받지 않는 것과 동일한 원칙)
    """

    name: str = Field(min_length=1, examples=["따뜻한 소년 목소리"])
    description: str | None = None
    voicePrompt: str | None = None  # 원하는 목소리 설명(사용자 의도). appearancePrompt와 같은 성격

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class VoiceUpdateRequest(BaseModel):
    """보이스 메타 수정 — 사용자가 정하는 name/description/voicePrompt만 받는다.

    provider/model/sampleAudioUrl/status는 AI/TTS 파트가 채우는 결과 필드라
    백엔드 수정 API로 받지 않는다. (TTS audioUrl을 백엔드가 안 받는 것과 동일 원칙)
    """

    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    voicePrompt: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _not_blank(value)


class VoiceResponse(BaseModel):
    voiceId: str
    name: str
    description: str | None = None
    voicePrompt: str | None = None
    sampleAudioUrl: str | None = None
    provider: str | None = None
    model: str | None = None
    # 생성 직후 "pending"(AI 클로닝 대기). 실제 클로닝/상태 갱신은 AI/TTS 파트가 한다.
    status: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "voiceId": "voice_mock_001",
                "name": "따뜻한 소년 목소리",
                "description": "밝고 호기심 많은 소년 톤",
                "voicePrompt": "warm, curious young boy voice",
                "sampleAudioUrl": None,
                "provider": None,
                "model": None,
                "status": "pending",
            }
        }
    )


class VoiceDeleteResponse(BaseModel):
    deleted: bool
    voiceId: str

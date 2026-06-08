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
    """보이스 선택 화면용 응답.

    provider/model은 AI/TTS 내부 메타라 사용자 화면에 필요 없어 응답에서 제외한다.
    (내부 repository에는 보관하지만 노출하지 않음 — 캐릭터에서 seed/model을 안 받는 것과 동일 원칙)
    """

    voiceId: str
    name: str
    description: str | None = None
    voicePrompt: str | None = None
    voiceType: str  # narrator / character (추천 용도)
    isPreset: bool  # True면 시스템 기본 보이스 (수정/삭제 불가)
    # 생성 직후 "pending"(AI 클로닝 대기). preset은 "ready". 상태 갱신은 AI/TTS 파트가 한다.
    status: str
    # 미리듣기 샘플 URL. AI/TTS 파트가 채우며 현재는 null일 수 있음.
    sampleAudioUrl: str | None = None
    durationSec: float | None = None
    # 클로닝 보이스용 필드(없으면 null). referenceAudioPath(절대경로)는 절대 노출하지 않는다.
    speakerLabel: str | None = None  # 누가 녹음했는지(엄마/아이/아빠 등). voiceType과 독립.
    characterId: str | None = None
    referenceAudioUrl: str | None = None
    referenceText: str | None = None
    error: str | None = None
    createdAt: str | None = None
    updatedAt: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "voiceId": "voice_preset_narrator_calm_001",
                "name": "차분한 나레이션",
                "description": "잔잔하고 따뜻하게 동화를 읽어주는 목소리",
                "voicePrompt": "calm, warm, gentle narrator voice for fairy tale storytelling",
                "voiceType": "narrator",
                "isPreset": True,
                "status": "ready",
                "sampleAudioUrl": None,
            }
        }
    )


class VoiceDeleteResponse(BaseModel):
    deleted: bool
    voiceId: str


class VoiceCloneJobResponse(BaseModel):
    """보이스 클로닝 시작(POST /api/voices/clone) 즉시 응답. 상세는 GET /api/jobs/{jobId} 폴링."""

    jobId: str
    voiceId: str
    status: str = Field(description="생성 직후 보통 pending")
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "jobId": "job_mock_001",
                "voiceId": "voice_mock_001",
                "status": "pending",
                "message": "Voice cloning job started.",
            }
        }
    )

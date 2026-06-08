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


class SceneCharacterLayout(BaseModel):
    """씬 합성 미리보기에서 캐릭터의 배치 정보.

    좌표는 **정규화(0~1)** 로 저장한다(미리보기 크기 ≠ 최종 렌더 해상도여도 동일 위치로 매핑).
    x/y는 캐릭터의 **중심** 위치, scale은 스테이지 너비 대비 캐릭터 너비 비율.
    """

    # 백엔드 계약은 백엔드가 지킨다(프론트 clamp는 방어용일 뿐). 범위 밖 값은 422.
    x: float = Field(default=0.5, ge=0.0, le=1.0)  # 중심 x (정규화)
    y: float = Field(default=0.55, ge=0.0, le=1.0)  # 중심 y (정규화)
    scale: float = Field(default=0.28, gt=0.0, le=5.0)  # 너비 비율(양수, 과도값 방지)
    rotation: float = Field(default=0.0, ge=-360.0, le=360.0)  # 각도(도). 해상도 무관
    zIndex: int = Field(default=1, ge=0, le=9999)
    flipX: bool = False


class SceneCharacterItem(BaseModel):
    """씬에 연결된 캐릭터 1개. (씬당 여러 명 가능)"""

    characterId: str
    # 씬별 캐릭터 연출(표정/포즈 등). 지금은 저장만 하고,
    # 추후 face_lock / pose_expression / scene character generation 에서 사용한다.
    sceneAppearancePrompt: str | None = None
    # 합성 미리보기 배치(위치/크기/순서/반전). 없으면 프론트/서비스 기본값 사용.
    layout: SceneCharacterLayout | None = None
    # 이 씬에서 이 캐릭터가 쓸 포즈. None이면 원본 character.imageUrl 사용(씬 단위 override, 전역 불변).
    poseId: str | None = None
    # 표시용 이미지(백엔드 해석: poseId 있으면 포즈, 없으면 원본). 응답에만 채워짐(저장 X).
    imageUrl: str | None = None


class SceneCharacterPoseUpdateRequest(BaseModel):
    """PATCH /api/scenes/{sceneId}/characters/{characterId}/pose 의 body.

    현재 씬의 캐릭터 연결에 poseId를 지정/해제한다(씬 단위). poseId=null이면 기본 이미지로 되돌림.
    """

    storyId: str
    poseId: str | None = None


class SceneCharacterUpdateRequest(BaseModel):
    """PATCH /api/scenes/{sceneId}/character 의 body. 씬에 캐릭터를 추가/수정한다.

    씬당 여러 캐릭터를 둘 수 있다. 같은 characterId면 sceneAppearancePrompt만 갱신.
    개별 제거는 DELETE /api/scenes/{sceneId}/character/{characterId}.
    """

    storyId: str
    characterId: str
    sceneAppearancePrompt: str | None = None
    # 위치/크기 조정 저장용. 전달되면 그 캐릭터의 layout만 갱신한다.
    layout: SceneCharacterLayout | None = None


class SceneCharactersResponse(BaseModel):
    storyId: str
    sceneId: str
    characters: list[SceneCharacterItem] = []


class CharacterPoseResponse(BaseModel):
    """생성된 포즈 1개. (포즈 생성 Job의 result, 포즈 목록 조회 항목, CharacterResponse.poses 공용)"""

    poseId: str
    characterId: str
    posePrompt: str
    imageUrl: str


class CharacterResponse(BaseModel):
    characterId: str = Field(description="char_mock_001 형식으로 자동 생성")
    name: str
    appearancePrompt: str
    imageUrl: str | None = Field(default=None, description="생성된 원본 이미지 경로. 없으면 null")
    voiceId: str | None = Field(default=None, description="연결된 보이스 ID. 없으면 null")
    # 참고: 포즈 목록은 GET /api/characters/{id}/poses 로 따로 조회(목록 응답을 가볍게 유지).
    #       씬에서의 표시 이미지는 백엔드가 story/timeline 응답에서 해석해 내려준다.
    #       aiImagePath(AI 서버 원본 경로)는 내부 전용 — 응답에 노출하지 않는다.

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


class PoseGenerateRequest(BaseModel):
    """POST /api/characters/{characterId}/poses/generate body. (characterId는 URL path)"""

    posePrompt: str = Field(min_length=1, examples=["running in the snow"])

    @field_validator("posePrompt")
    @classmethod
    def not_blank(cls, value: str) -> str:
        return _not_blank(value)

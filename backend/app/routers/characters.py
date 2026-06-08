from fastapi import APIRouter

from ..schemas.character import (
    CharacterCreateRequest,
    CharacterDeleteResponse,
    CharacterGenerateRequest,
    CharacterPoseResponse,
    CharacterResponse,
    CharacterUpdateRequest,
    CharacterVoiceUpdateRequest,
    PoseDeleteResponse,
    PoseGenerateRequest,
)
from ..schemas.job import JobCreatedResponse
from ..services.character_job_runner import create_character_generation_job
from ..services.character_pose_job_runner import create_character_pose_generation_job
from ..services.character_service import character_service

router = APIRouter(prefix="/api/characters", tags=["characters"])


@router.post(
    "/generate",
    response_model=JobCreatedResponse,
    summary="캐릭터 생성 Job 요청",
)
def generate_character(request: CharacterGenerateRequest):
    """
    캐릭터 생성을 **비동기 Job**으로 요청합니다.

    ComfyUI로 실제 이미지를 생성하며, **jobId와 `status="pending"`을 즉시 반환**합니다.
    실제 생성은 백그라운드(InMemoryJobManager.run_async, ThreadPoolExecutor)에서 진행되고,
    클라이언트는 `GET /api/jobs/{jobId}`로 pending→running→completed/failed를 폴링합니다.

    생성 실패 시 캐릭터 레코드는 저장되지 않습니다(orphan 방지: 성공 후 저장).
    나중에 RabbitMQ/Celery publish 로직으로 교체할 수 있습니다.
    """
    return create_character_generation_job(request.model_dump())


@router.get("", response_model=list[CharacterResponse], summary="캐릭터 목록 조회")
def list_characters():
    """메모리 Mock Repository에 저장된 캐릭터 목록을 전부 반환합니다."""
    return character_service.list_characters()


@router.post("", response_model=CharacterResponse, summary="캐릭터 직접 저장")
def create_character(request: CharacterCreateRequest):
    """
    이미 만들어진 캐릭터 결과를 직접 저장합니다.

    generate API와 별도이며, 외부 생성 결과 저장 / 테스트용 등록 /
    나중에 worker가 결과를 저장할 때 사용합니다.
    """
    return character_service.create_character(request.model_dump())


@router.get("/{character_id}", response_model=CharacterResponse, summary="캐릭터 단건 조회")
def get_character(character_id: str):
    """
    characterId로 캐릭터 하나를 조회합니다.

    - characterId 예시: `char_mock_001`
    - 존재하지 않으면 404(`Character not found`)를 반환합니다.
    """
    return character_service.get_character(character_id)


@router.patch(
    "/{character_id}", response_model=CharacterResponse, summary="캐릭터 부분 수정"
)
def update_character(character_id: str, request: CharacterUpdateRequest):
    """
    캐릭터 정보를 부분 수정합니다. (name / appearancePrompt / imageUrl)

    - 전달된 필드만 반영합니다.
    - 수정 가능한 필드가 하나도 없으면 400(`No fields to update`)을 반환합니다.
    - 존재하지 않으면 404(`Character not found`)를 반환합니다.
    """
    return character_service.update_character(
        character_id, request.model_dump(exclude_unset=True)
    )


@router.delete(
    "/{character_id}",
    response_model=CharacterDeleteResponse,
    summary="캐릭터 삭제",
)
def delete_character(character_id: str):
    """
    캐릭터를 삭제합니다.

    - 존재하지 않으면 404(`Character not found`)를 반환합니다.
    """
    character_service.delete_character(character_id)
    return {"deleted": True, "characterId": character_id}


@router.patch(
    "/{character_id}/voice",
    response_model=CharacterResponse,
    summary="캐릭터에 보이스 연결",
)
def update_character_voice(character_id: str, request: CharacterVoiceUpdateRequest):
    """
    캐릭터에 보이스(라이브러리)의 voiceId를 연결한다.

    - body: `{"voiceId": "voice_mock_001"}` (null이면 연결 해제)
    - 보이스가 없으면 404(`Voice not found`), 캐릭터가 없으면 404(`Character not found`).
    """
    return character_service.update_character_voice(character_id, request.voiceId)


@router.post(
    "/{character_id}/poses/generate",
    response_model=JobCreatedResponse,
    summary="캐릭터 포즈 생성 Job 요청",
)
def generate_character_pose(character_id: str, request: PoseGenerateRequest):
    """
    기존 캐릭터를 reference 로 새 포즈를 **비동기 Job**으로 생성한다. (characterId는 URL path)

    - body: `{"posePrompt": "running in the snow"}` (빈 문자열 → 422)
    - 백엔드가 characterId로 캐릭터를 조회해 내부 aiImagePath를 꺼내 AI 서버 `/generate-pose`에 전달.
      프론트는 image_path를 알거나 보내지 않는다.
    - 캐릭터 없음 → 404, aiImagePath 없음(기능 추가 전 생성 등) → 400.
    - jobId 즉시 반환, `GET /api/jobs/{jobId}`로 폴링. 완료 result = CharacterPoseResponse.
    """
    # 검증은 동기로(404/400 즉시), 생성만 비동기 Job.
    ai_image_path = character_service.get_pose_source(character_id)
    return create_character_pose_generation_job(character_id, ai_image_path, request.posePrompt)


@router.get(
    "/{character_id}/poses",
    response_model=list[CharacterPoseResponse],
    summary="캐릭터 포즈 목록 조회",
)
def list_character_poses(character_id: str):
    """캐릭터에 생성된 포즈 목록(1:N). 캐릭터 없음 → 404."""
    return character_service.list_poses(character_id)


@router.delete(
    "/{character_id}/poses/{pose_id}",
    response_model=PoseDeleteResponse,
    summary="캐릭터 포즈 삭제",
)
def delete_character_pose(character_id: str, pose_id: str):
    """캐릭터 포즈 1개 삭제. 캐릭터/포즈 없음 → 404, 씬에서 사용 중인 포즈 → 409(삭제 차단)."""
    return character_service.delete_pose(character_id, pose_id)

from fastapi import APIRouter

from ..schemas.character import (
    CharacterCreateRequest,
    CharacterDeleteResponse,
    CharacterGenerateJobResponse,
    CharacterGenerateRequest,
    CharacterResponse,
    CharacterUpdateRequest,
)
from ..services.character_job_runner import create_character_generation_job
from ..services.character_service import character_service

router = APIRouter(prefix="/api/characters", tags=["characters"])


@router.post(
    "/generate",
    response_model=CharacterGenerateJobResponse,
    summary="캐릭터 생성 Job 요청",
)
def generate_character(request: CharacterGenerateRequest):
    """
    캐릭터 생성을 비동기 Job 구조로 요청합니다.

    실제 ComfyUI 호출 없이 mock 캐릭터 결과를 만들어 저장하고,
    jobId와 status를 반환합니다. (현재 mock 구현은 즉시 `completed`)

    생성 흐름은 InMemoryJobManager가 담당하며, 나중에 RabbitMQ/Celery
    publish 로직으로 교체할 수 있습니다.
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

from fastapi import APIRouter

from ..schemas.background import (
    BackgroundCreateRequest,
    BackgroundDeleteResponse,
    BackgroundGenerateRequest,
    BackgroundPromptSuggestionRequest,
    BackgroundPromptSuggestionResponse,
    BackgroundResponse,
    BackgroundUpdateRequest,
)
from ..schemas.job import JobCreatedResponse
from ..services.background_service import background_service
from ..services.job_manager import job_manager

router = APIRouter(prefix="/api/backgrounds", tags=["backgrounds"])


@router.post(
    "/prompt-suggestions",
    response_model=BackgroundPromptSuggestionResponse,
    summary="씬 기반 배경 프롬프트 추천",
)
def suggest_background_prompt(request: BackgroundPromptSuggestionRequest):
    """
    storyId/sceneId로 scene.items를 읽어 규칙 기반 배경 프롬프트 초안을 만든다.

    - 이미지 생성은 하지 않는다. 프롬프트 초안만 반환한다.
    - narration 우선, 없으면 dialogue로 sourceText를 만들고 키워드를 매칭한다.
    - 키워드가 없으면 기본 suggestedPrompt를 반환한다.
    - finalPrompt에는 background only / no characters 규칙이 포함된다.
    """
    return background_service.suggest_prompt(request.storyId, request.sceneId)


@router.post(
    "/generate",
    response_model=JobCreatedResponse,
    summary="배경 후보 생성 Job",
)
def generate_backgrounds(request: BackgroundGenerateRequest):
    """
    배경 후보를 생성하는 Job을 만든다. (현재 mock, 즉시 completed)

    실제 ComfyUI 호출 없이 mock candidate를 만들어 임시 저장하고,
    jobId/status를 반환한다. 후보는 GET /api/jobs/{jobId}에서 확인한다.
    (후보 개수는 ComfyUI 워크플로가 결정하며 mock은 4장을 가정한다.)

    ⚠️ prompt 계약: 여기 넣는 `prompt`는 **맨 프롬프트**(suggestedPrompt 또는 사용자가
    수정한 원본 prompt)여야 한다. background only/no characters 등 suffix가 붙은
    `finalPrompt`를 그대로 보내면 suffix가 중복된다. finalPrompt는 백엔드가 조립한다.
    """
    return job_manager.create_background_generation_job(request.model_dump())


@router.post("", response_model=BackgroundResponse, summary="후보 1장 배경 라이브러리 저장")
def create_background(request: BackgroundCreateRequest):
    """
    생성된 후보(candidateId) 중 하나를 골라 배경 라이브러리에 저장한다.

    - candidateId가 없으면 404(Background candidate not found)를 반환한다.
    - 저장된 Background는 여러 스토리/씬에서 재사용할 수 있다.
    """
    return background_service.save_background(request.candidateId, request.name)


@router.get("", response_model=list[BackgroundResponse], summary="저장된 배경 목록 조회")
def list_backgrounds():
    """저장된 배경 라이브러리 전체를 반환한다."""
    return background_service.list_backgrounds()


@router.get("/{background_id}", response_model=BackgroundResponse, summary="저장된 배경 단건 조회")
def get_background(background_id: str):
    """
    backgroundId로 저장된 배경을 조회한다. (후보가 아니라 저장된 배경)

    - 존재하지 않으면 404(Background not found)를 반환한다.
    """
    return background_service.get_background(background_id)


@router.patch("/{background_id}", response_model=BackgroundResponse, summary="배경 수정 (name)")
def update_background(background_id: str, request: BackgroundUpdateRequest):
    """
    저장된 배경을 수정한다. MVP에서는 name만 수정 가능하다.

    - 수정 가능한 필드가 하나도 없으면 400(No fields to update)를 반환한다.
    - 존재하지 않으면 404(Background not found)를 반환한다.
    """
    return background_service.update_background(
        background_id, request.model_dump(exclude_unset=True)
    )


@router.delete(
    "/{background_id}",
    response_model=BackgroundDeleteResponse,
    summary="배경 삭제 (+참조 씬 해제)",
)
def delete_background(background_id: str):
    """
    저장된 배경을 삭제한다.

    - 존재하지 않으면 404(Background not found)를 반환한다.
    - 삭제 시 이 배경을 참조하던 모든 scene의 backgroundId를 null로 만든다.
    """
    return background_service.delete_background(background_id)

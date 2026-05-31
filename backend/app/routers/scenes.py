from fastapi import APIRouter

from ..schemas.background import SceneBackgroundResponse, SceneBackgroundUpdateRequest
from ..services.background_service import background_service

router = APIRouter(prefix="/api/scenes", tags=["scenes"])


@router.patch(
    "/{scene_id}/background",
    response_model=SceneBackgroundResponse,
    summary="씬에 배경 연결",
)
def connect_scene_background(scene_id: str, request: SceneBackgroundUpdateRequest):
    """
    씬에 저장된 배경(backgroundId)을 연결한다.

    - storyId는 request body로 받는다. (sceneId는 story 내에서만 유니크할 수 있음)
    - 연결 대상은 candidateId가 아니라 저장된 backgroundId여야 한다.
    - story 없음 → 404(Story not found), scene 없음 → 404(Scene not found),
      background 없음 → 404(Background not found)
    """
    return background_service.connect_scene_background(
        request.storyId, scene_id, request.backgroundId
    )

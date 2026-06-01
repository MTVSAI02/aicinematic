from fastapi import APIRouter

from ..schemas.background import SceneBackgroundResponse, SceneBackgroundUpdateRequest
from ..schemas.character import SceneCharactersResponse, SceneCharacterUpdateRequest
from ..services.background_service import background_service
from ..services.character_service import character_service

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


@router.patch(
    "/{scene_id}/character",
    response_model=SceneCharactersResponse,
    summary="씬에 캐릭터 추가/수정 (씬당 다중)",
)
def connect_scene_character(scene_id: str, request: SceneCharacterUpdateRequest):
    """
    씬에 캐릭터를 추가하거나 수정한다. **씬당 여러 명** 가능.

    - storyId는 request body로 받는다.
    - 같은 characterId가 이미 있으면 sceneAppearancePrompt만 갱신한다.
    - sceneAppearancePrompt(표정/포즈 등 씬별 연출)는 지금은 scene에 저장만 한다.
    - 개별 제거는 `DELETE /api/scenes/{sceneId}/character/{characterId}`.
    - story 없음 → 404, scene 없음 → 404, character 없음 → 404.
    - 반환: 그 씬의 전체 캐릭터 목록.
    """
    return character_service.connect_scene_character(
        request.storyId,
        scene_id,
        request.characterId,
        request.sceneAppearancePrompt,
        request.layout.model_dump() if request.layout else None,
    )


@router.delete(
    "/{scene_id}/character/{character_id}",
    response_model=SceneCharactersResponse,
    summary="씬에서 캐릭터 1명 제거",
)
def disconnect_scene_character(scene_id: str, character_id: str, storyId: str):
    """
    씬에서 캐릭터 1명을 제거한다. (storyId는 쿼리 파라미터)

    - 없는 캐릭터를 제거해도 에러가 아니다(idempotent).
    - story 없음 → 404, scene 없음 → 404.
    - 반환: 남은 캐릭터 목록.
    """
    return character_service.disconnect_scene_character(storyId, scene_id, character_id)

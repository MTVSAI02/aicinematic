from fastapi import APIRouter

from ..schemas.background import SceneBackgroundResponse, SceneBackgroundUpdateRequest
from ..schemas.character import (
    SceneCharacterPoseUpdateRequest,
    SceneCharactersResponse,
    SceneCharacterUpdateRequest,
)
from ..schemas.text_overlay import (
    SceneSubtitleSettingsRequest,
    SceneTextOverlaysResponse,
)
from ..services.background_service import background_service
from ..services.character_service import character_service
from ..services.text_overlay_service import text_overlay_service

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


@router.patch(
    "/{scene_id}/characters/{character_id}/pose",
    response_model=SceneCharactersResponse,
    summary="씬 캐릭터에 포즈 적용/해제 (씬 단위)",
)
def set_scene_character_pose(
    scene_id: str, character_id: str, request: SceneCharacterPoseUpdateRequest
):
    """
    현재 씬의 캐릭터가 쓸 포즈를 지정/해제한다. (전역 원본 이미지는 바꾸지 않음 — 씬 단위 override)

    - body: `{"storyId": "...", "poseId": "pose_mock_001"}` — `poseId=null`이면 기본(원본) 이미지로.
    - story/scene 없음 → 404, 씬에 연결 안 된 캐릭터 → 404, 그 캐릭터의 포즈가 아니면 → 404.
    - 반환: 그 씬의 캐릭터 목록(각 항목에 poseId 포함).
    """
    return character_service.set_scene_character_pose(
        request.storyId, scene_id, character_id, request.poseId
    )


@router.patch(
    "/{scene_id}/subtitles",
    response_model=SceneTextOverlaysResponse,
    summary="씬 자막 설정(cue 그룹 + 배치) 저장",
)
def update_scene_subtitles(scene_id: str, request: SceneSubtitleSettingsRequest):
    """
    씬 자막들의 **cue 그룹(cueOrder) + 배치(layout)만** 저장한다.

    - 자막은 대본(items)에서 줄당 1개 자동 생성 → **추가/텍스트 변경 없음.**
    - 기본 cueOrder = 줄 순번+1(각 줄이 자기 cue). 사용자가 다른 줄을 기존 cue 그룹에 묶을 수 있다.
    - itemIndex 범위 밖은 무시. cueOrder/layout 범위 위반 → 422. story/scene 없음 → 404.
    - 반환: items + 저장 설정으로 조립한 자막 목록.
    """
    return text_overlay_service.update_subtitles(
        request.storyId, scene_id, request.overlays
    )

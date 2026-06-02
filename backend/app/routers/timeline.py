from fastapi import APIRouter

from ..schemas.timeline import RenderPlanResponse, TimelineResponse, TimelineUpdateRequest
from ..services.timeline_service import timeline_service

router = APIRouter(prefix="/api/stories", tags=["timeline"])


@router.get("/{story_id}/timeline", response_model=TimelineResponse, summary="타임라인 조회")
def get_timeline(story_id: str):
    """story 의 scene 을 order 기준으로 정렬해 타임라인 정보를 반환한다.

    - duration 이 없는 기존 scene 은 3.0 으로 보정.
    - 각 scene: textPreview / background summary / characters summary / readyStatus.
    - totalDuration 은 scene duration 합. 존재하지 않는 storyId → 404.
    """
    return timeline_service.get_timeline(story_id)


@router.patch("/{story_id}/timeline", response_model=TimelineResponse, summary="타임라인 저장(전체)")
def update_timeline(story_id: str, request: TimelineUpdateRequest):
    """씬별 재생 길이(duration)와 자막 cue 타이밍(cueTimings)을 저장한다. **전체 scene 목록**을 받는다(부분 업데이트 X).

    - 순서(order)는 스토리 원본 그대로 유지한다(타임라인은 재배치하지 않음). 자막 텍스트/위치/cueOrder 는 안 바뀜 — 시간만.
    - 요청은 story 의 모든 scene 을 정확히 한 번씩 포함해야 함(누락/초과/중복 → 400).
    - cueTimings(선택): 씬에 없는 cueOrder / cueOrder 중복 / 씬 duration 초과 → 400. cueTimings 미전송 시 기존값을 새 duration 안으로 클램프.
    - 모든 scene 을 먼저 검증한 뒤 한 번에 반영(atomic) — 한 건이라도 실패하면 아무것도 안 바뀜.
    - 존재하지 않는 sceneId → 404. duration(1.0~30.0)·cue 범위 위반 → 422.
    """
    return timeline_service.update_timeline(story_id, request.scenes)


@router.get("/{story_id}/render-plan", response_model=RenderPlanResponse, summary="렌더 플랜(2차 렌더용 데이터)")
def get_render_plan(story_id: str):
    """2차 ffmpeg 렌더가 그대로 사용할 데이터 구조를 만든다. (실제 렌더/파일 생성은 안 함)

    scene별 duration / backgroundImageUrl / characters(layout 포함) / subtitles / totalDuration.
    """
    return timeline_service.build_render_plan(story_id)

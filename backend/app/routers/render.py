from fastapi import APIRouter

from ..schemas.render import RenderJobResponse, RenderStatusResponse
from ..services.render_service import create_render_job, get_last_render

router = APIRouter(prefix="/api/stories", tags=["render"])


@router.get("/{story_id}/render", response_model=RenderStatusResponse, summary="스토리 최신 렌더 결과 조회")
def get_render(story_id: str):
    """스토리의 최신 렌더 결과(lastRender)를 조회한다. 새로고침 시 기존 영상 복원용.

    - lastRender 있으면 그 videoUrl 을 바로 표시(재렌더링 X). 없으면 lastRender=null → [영상 생성] 버튼.
    - 없는 storyId → 404.
    """
    return get_last_render(story_id)


@router.post("/{story_id}/render", response_model=RenderJobResponse, summary="영상 렌더링(무음 mp4) 시작")
def start_render(story_id: str):
    """story 의 render plan 으로 무음 mp4 렌더링 Job 을 시작한다(비동기).

    - 입력은 build_render_plan(storyId) 결과만 사용한다(배경/캐릭터/포즈/자막/cueTimings).
    - 오디오/TTS 없음 — 무음 영상 MVP. 사용자가 [영상 생성]/[다시 생성]을 명시적으로 누를 때만 호출.
    - story 없음 → 404, render plan 비었음 → 400. 즉시 jobId 반환 후 GET /api/jobs/{jobId} 폴링.
    - 완료 시 story.lastRender 저장(새로고침 후 GET 으로 복원). ffmpeg 미설치 시 Job failed + 명확한 에러.
    """
    return create_render_job(story_id)

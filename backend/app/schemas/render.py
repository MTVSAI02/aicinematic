from pydantic import BaseModel, ConfigDict, Field


class RenderJobResponse(BaseModel):
    """렌더 요청(POST /render)의 즉시 응답. (JobCreatedResponse 와 동일 형태)

    상세 결과는 GET /api/jobs/{jobId} 로 폴링한다.
    """

    jobId: str = Field(description="job_mock_001 형식으로 자동 생성")
    status: str = Field(description="생성 Job 상태 (보통 pending)")
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "jobId": "job_mock_001",
                "status": "pending",
                "message": "Render job started.",
            }
        }
    )


class RenderResult(BaseModel):
    """렌더 완료 시 Job result 에 담기는 값 (GET /api/jobs/{jobId} 의 result)."""

    renderId: str
    storyId: str
    videoUrl: str = Field(description="/storage/renders/{renderId}.mp4")
    duration: float = Field(description="전체 영상 길이(초)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "renderId": "render_ab12cd34ef56",
                "storyId": "story_mock_001",
                "videoUrl": "/storage/renders/render_ab12cd34ef56.mp4",
                "duration": 15.5,
            }
        }
    )


class LastRender(BaseModel):
    """story 에 저장되는 최신 렌더 결과(스토리당 1개)."""

    renderId: str
    videoUrl: str = Field(description="/storage/renders/{renderId}.mp4")
    duration: float
    createdAt: str = Field(description="ISO8601 생성 시각")


class RenderStatusResponse(BaseModel):
    """GET /api/stories/{storyId}/render — 새로고침 시 기존 영상 복원용. 없으면 lastRender=null."""

    storyId: str
    lastRender: LastRender | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "storyId": "story_mock_001",
                "lastRender": {
                    "renderId": "render_ab12cd34ef56",
                    "videoUrl": "/storage/renders/render_ab12cd34ef56.mp4",
                    "duration": 15.5,
                    "createdAt": "2026-06-03T00:00:00+00:00",
                },
            }
        }
    )

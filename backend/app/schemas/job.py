from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class JobStatus(str, Enum):
    """Job 상태 값.

    나중에 RabbitMQ/Celery 기반 비동기 처리로 확장할 때도 그대로 재사용한다.
    문자열 비교/직렬화가 가능하도록 str을 함께 상속한다.
    """

    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class JobType(str, Enum):
    """작업 유형. 이번 단계에서는 character_generate만 사용한다."""

    character_generate = "character_generate"


class JobResponse(BaseModel):
    jobId: str = Field(description="job_mock_001 형식으로 자동 생성")
    type: JobType = Field(description="작업 유형")
    status: JobStatus = Field(description="pending / running / completed / failed")
    progress: int = Field(description="작업 진행률 (0~100)")
    result: dict | None = Field(default=None, description="완료된 경우 생성된 결과")
    error: str | None = Field(default=None, description="실패한 경우 에러 메시지")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "jobId": "job_mock_001",
                "type": "character_generate",
                "status": "completed",
                "progress": 100,
                "result": {
                    "characterId": "char_mock_001",
                    "name": "어린왕자",
                    "appearancePrompt": "금발 단발, 초록 외투를 입은 작은 소년",
                    "imageUrl": None,
                },
                "error": None,
            }
        }
    )

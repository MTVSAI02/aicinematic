"""ai/ 모듈 공통 예외.

이 폴더는 FastAPI 서버가 아니므로 HTTPException / JSONResponse 등에 의존하지 않는다.
순수 Python 예외 계층만 정의하며, HTTP 응답 변환은 backend/app 계층(JobManager 등)이
이 예외들을 잡아서 처리한다. (예: ComfyUIError 발생 → job_repo.fail(job_id, error))
"""


class AIError(Exception):
    """ai/ 모듈 전체의 베이스 예외."""

    def __init__(self, message: str = "AI module error"):
        self.message = message
        super().__init__(message)


class ComfyUIError(AIError):
    """ComfyUI 연동 관련 베이스 예외."""

    def __init__(self, message: str = "ComfyUI error"):
        super().__init__(message)


class ComfyUIConfigError(ComfyUIError):
    """ComfyUI 설정값이 없거나 잘못된 경우."""

    def __init__(self, message: str = "ComfyUI configuration error"):
        super().__init__(message)


class ComfyUIConnectionError(ComfyUIError):
    """ComfyUI 서버 연결에 실패한 경우."""

    def __init__(self, message: str = "Failed to connect to ComfyUI server"):
        super().__init__(message)


class ComfyUIResponseError(ComfyUIError):
    """ComfyUI 응답이 유효하지 않거나 예상과 다른 경우 (non-200, JSON 파싱 실패 등)."""

    def __init__(self, message: str = "ComfyUI returned an invalid response"):
        super().__init__(message)


class ComfyUITimeoutError(ComfyUIError):
    """ComfyUI 요청이 timeout 된 경우."""

    def __init__(self, message: str = "ComfyUI request timed out"):
        super().__init__(message)


class WorkflowLoadError(ComfyUIError):
    """workflow JSON 파일을 읽지 못한 경우 (파일 없음 / JSON 파싱 실패 등)."""

    def __init__(self, message: str = "Failed to load workflow JSON"):
        super().__init__(message)


class WorkflowMappingError(ComfyUIError):
    """mapping JSON이 없거나, mapping이 가리키는 노드/경로가 workflow에 없는 경우."""

    def __init__(self, message: str = "Failed to apply workflow mapping"):
        super().__init__(message)


class BackgroundWorkflowPrepareError(ComfyUIError):
    """배경 workflow payload 준비 중 문제가 발생한 경우."""

    def __init__(self, message: str = "Failed to prepare background workflow"):
        super().__init__(message)

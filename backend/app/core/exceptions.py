class AppException(Exception):
    """애플리케이션 공통 예외 베이스.

    각 예외는 HTTP 상태 코드와 detail 메시지를 가지며,
    main.py에 등록된 글로벌 핸들러가 이를 HTTP 응답으로 변환한다.
    """

    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None):
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class CharacterNotFoundError(AppException):
    status_code = 404
    detail = "Character not found"


class JobNotFoundError(AppException):
    status_code = 404
    detail = "Job not found"


class NoFieldsToUpdateError(AppException):
    status_code = 400
    detail = "No fields to update"


class CharacterGenerationFailedError(AppException):
    status_code = 500
    detail = "Character generation failed"

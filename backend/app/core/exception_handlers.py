from fastapi import Request
from fastapi.responses import JSONResponse

from .exceptions import AppException


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """AppException 계열 예외를 일관된 JSON 응답으로 변환한다."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

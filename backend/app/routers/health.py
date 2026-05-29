from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", summary="헬스 체크")
def health():
    """
    백엔드 서버가 정상적으로 실행 중인지 확인합니다.

    프론트엔드 개발 서버 연동 확인용으로 사용합니다.
    """
    return {"status": "ok", "message": "Mongsil Bookstore backend is running"}

"""AI Cinematic 백엔드 진입점.

CORS 설정과 헬스체크 엔드포인트를 둔다.
실행: uv run uvicorn backend.app.main:app --reload
문서: http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI Cinematic API", version="0.1.0")

# 프론트(Vite 개발 서버) 에서의 호출 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    """프론트-백엔드 연동 확인용 헬스체크."""
    return {"status": "ok", "service": "ai-cinematic-backend"}

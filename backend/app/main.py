from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.exception_handlers import app_exception_handler
from .core.exceptions import AppException
from .routers import characters, health, jobs, stories

app = FastAPI(
    title="Mongsil Bookstore API",
    description="Backend API for AI-based moving storybook service",
    version="0.1.0",
)

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

app.add_exception_handler(AppException, app_exception_handler)

app.include_router(health.router)
app.include_router(stories.router)
app.include_router(characters.router)
app.include_router(jobs.router)


@app.get("/")
def root():
    return {"service": "Mongsil Bookstore", "status": "running", "docs": "/docs"}

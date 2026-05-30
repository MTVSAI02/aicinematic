# ⚠️ 임시 코드: AI(ComfyUI) 연결 테스트용 — 실제 연동 시 삭제/교체

이 문서는 **임시로 추가한 "연결 확인용 코드"** 목록과 제거 기준을 적어둔다.

## 왜 임시인가

현재는 백엔드 `JobManager`가 ComfyUI를 실제로 호출하지 않는다(mock 캐릭터 생성).
그래서 "프론트 → 백엔드 → AI → ComfyUI → 백엔드 → 프론트" 전체 경로가 **한 번에 도는지 확인**하기 위해,
ComfyUI의 **읽기전용** API(`/system_stats`, `/object_info`)만 호출하는 연결 확인 통로를 임시로 만들었다.

- ComfyUI **이미지 생성(`POST /prompt`)은 호출하지 않는다.** (읽기전용 health check 뿐)

## 🗑️ 제거 기준 (언제 지우나)

**실제 ComfyUI 연동이 구현되면 삭제하거나 정식 구조로 교체한다.**

구체적으로 아래가 충족되는 시점:

- 백엔드 `InMemoryJobManager`(또는 RabbitMQ/Celery worker)가 실제로 `ai` 모듈을 통해
  ComfyUI workflow를 실행해 캐릭터 이미지를 생성하도록 연결될 때.
- 즉 `프론트 → 백엔드 → AI → ComfyUI` 가 mock이 아니라 실제 생성 흐름으로 동작할 때.

> 그 단계에서 `/api/ai/comfy-health`는 (1) 완전히 삭제하거나,
> (2) 정식 헬스체크/모니터링 엔드포인트로 승격할지 팀에서 결정한다.

## 삭제 대상 체크리스트

### 백엔드
- [ ] `backend/app/routers/ai_health.py` — 파일 전체 (`GET /api/ai/comfy-health`, `GET /api/ai/background-comfy-health`)
- [ ] `backend/app/main.py`
  - [ ] `from .routers import ai_health, ...` 에서 `ai_health` 제거
  - [ ] `app.include_router(ai_health.router)` 줄 제거
- [ ] 백엔드 실행 시 주입한 `COMFYUI_DEFAULT_URL` 처리
  - 현재는 이 엔드포인트 때문에 백엔드를 `uv run --env-file ai/.env uvicorn ...` 로 띄워야 동작한다.
  - 실제 연동 단계에서 AI 설정(env)을 backend config로 정식 편입할지 함께 정리한다.

### 프론트엔드
- [ ] `frontend/src/api/ai.js` — 파일 전체 (`getComfyHealth`, `getBackgroundComfyHealth`)
- [ ] `frontend/src/components/AiConnectionCheck.jsx` — 파일 전체 (연결 확인 버튼 컴포넌트, check/label/okText props)
- [ ] `frontend/src/pages/character/CharacterPage.jsx`
  - [ ] `import AiConnectionCheck from '@/components/AiConnectionCheck'`
  - [ ] `<AiConnectionCheck />` 렌더링 (`{/* 임시: AI(ComfyUI) 연결 확인 ... */}`)
- [ ] `frontend/src/pages/background/BackgroundPage.jsx`
  - [ ] `import AiConnectionCheck` / `import { getBackgroundComfyHealth }`
  - [ ] `<AiConnectionCheck check={getBackgroundComfyHealth} ... />` 렌더링 (`{/* 임시: 배경 전용 경로 연결 확인 ... */}`)
- [ ] `frontend/src/pages/character/CharacterPage.module.css` — `.aiCheck` 클래스

## 유지해도 되는 것 (임시 아님)

아래는 정식 AI 모듈이므로 이 정리와 무관하게 유지한다.

- `ai/comfy_client.py`, `ai/core/exceptions.py` — ComfyUI 공통 클라이언트/예외 (정식)
- `ai/test_comfy_connection.py`, `ai/.env.example` — AI 파트 자체 연결 테스트 도구

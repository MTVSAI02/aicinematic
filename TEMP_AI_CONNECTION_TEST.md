# ⚠️ 임시 코드: AI 연결 테스트용 — 실제 연동 시 삭제/교체

이 문서는 **임시로 추가한 "연결 확인용 코드"** 목록과 제거 기준을 적어둔다.

## 현재 상태 (2026-06 기준)

캐릭터·배경은 **외부 AI FastAPI 서버 방식**(`Backend → AI 서버(/generate-character·/generate-background) → ComfyUI`)으로
전환·검증되었다. 그래서 ComfyUI를 **직접** 찔러보던 캐릭터/배경 연결 확인 임시 코드는 **제거 완료**다.

- ✅ 백엔드 `GET /api/ai/comfy-health`, `GET /api/ai/background-comfy-health` 제거
- ✅ `ai/image/background.py` 의 `check_background_comfy_connection()` 제거
- ✅ ai 연결 테스트 스크립트 제거 (`ai/character_ctrl/test_comfy_check.py`, `ai/test_comfy_connection.py`, `ai/test_background_connection.py`)
- ✅ 프론트 `getComfyHealth`/`getBackgroundComfyHealth` 및 캐릭터/배경 페이지의 `<AiConnectionCheck />` 제거
- 유지: 일반 서버 상태 확인 `/api/health` (ComfyUI 연결 확인 아님 — 영구 유지)

## 🗑️ 아직 남은 정리 대상 (TTS/Voice)

TTS/Voice는 **아직 실제 AI 서버 연동 테스트 전**이라, 보이스 연결 확인 임시 코드는 **그대로 둔다.**
TTS 실연동 테스트가 끝나면 아래를 제거한다.

### 백엔드
- [ ] `backend/app/routers/ai_health.py` — `GET /api/ai/voice-comfy-health` (현재 이 파일에 이 엔드포인트만 남음 → 제거 시 파일째 삭제 + `main.py`의 import/`include_router` 제거)
- [ ] `ai/voice/voice.py` 의 `check_voice_comfy_connection()`

### 프론트엔드
- [ ] `frontend/src/api/ai.js` — `getVoiceComfyHealth` (현재 이 함수만 남음 → 제거 시 파일째 삭제)
- [ ] `frontend/src/components/AiConnectionCheck.jsx` — 파일 전체 (현재 VoicePage에서만 사용)
- [ ] `frontend/src/pages/voice/VoicePage.jsx` — `import AiConnectionCheck` / `getVoiceComfyHealth` + `<AiConnectionCheck .../>` 렌더링
- [ ] `frontend/src/pages/character/CharacterPage.module.css` — `.aiCheck` 클래스 (VoicePage에서 더 이상 안 쓰면 제거)

## 유지 (임시 아님)
- `ai/comfy_client.py`, `ai/core/exceptions.py` — ComfyUI 공통 클라이언트/예외 (정식). 단, ComfyUI 직접 호출 내장 경로(`character.py`/`comfy_workflow_runner.py` 등)의 정리는 별도 작업으로 둔다.

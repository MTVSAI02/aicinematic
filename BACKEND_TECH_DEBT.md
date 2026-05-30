# 백엔드 / AI 구조 리뷰 — 보류/결정 기록

백엔드·AI 구조 리뷰에서 나온 항목들의 처리 결정을 남긴다.
(코드 주석/README만으로는 흩어지기 쉬운 "왜 지금 안 했는가 + 언제 할 것인가"를 한곳에 모은다.)

---

## 1. 보류 — 방향은 동의, 지금은 과설계(YAGNI)라 미룸

### 1.1 `services/job_manager.py` 분리
- 현재: 캐릭터 생성 + 배경 후보 생성 Job 로직을 한 클래스(`InMemoryJobManager`)가 보유 (약 131줄).
- 판단: 아직 읽을 만함. 지금 쪼개면 쓰지도 않을 계층이 늘어 오히려 복잡.
- **분리 트리거(이때 분리한다)**:
  - 도메인 Job 타입이 3~4개로 늘 때 (예: 음성/렌더링 Job 추가)
  - RabbitMQ/Celery 또는 ComfyUI 실제 비동기 연동이 붙을 때
- **분리 방향(예시)**: `InMemoryJobManager`는 Job 발급/상태 관리만 담당,
  도메인별 작업 로직(`character_job_runner`, `background_job_runner` 등)은 따로.

### 1.2 `services/background_service.py` 분리
- 현재: prompt suggestion + suffix 조립 + negative prompt + 배경 CRUD + 씬 연결/해제까지 한 파일 (약 174줄).
- 판단: 아직 응집도 OK. ComfyUI/LLM prompt enhancement가 붙으면 빠르게 비대해짐.
- **분리 트리거**: 실제 ComfyUI 호출 또는 LLM prompt enhancement 도입 시.
- **분리 방향(예시)**: `prompt_builder` / `background_library_service` / `scene_background_service`.

### 1.3b (프론트) `SceneEditorPage` 컴포넌트 분리
- 현재: 스토리 조회 + 배경 조회 + 씬 선택 + 배경 연결 + 캔버스 placeholder가 한 파일.
- 판단: 지금은 참을 만함. 캐릭터 배치/합성/미리보기가 들어오면 빠르게 커짐.
- **분리 트리거**: SceneEditor에 캐릭터 배정 또는 합성 미리보기가 추가될 때.
- **분리 방향(예시)**: `SceneStorySidebar` / `SceneCanvasPreview` / `SceneBackgroundPanel` / `SceneCharacterPanel`.

### 1.3 `ai/comfy_client.py` 에서 workflow loader/mapper 분리
- 현재: ComfyUI 연결/조회 클라이언트(`ComfyUIClient`)가 workflow JSON 로드 + mapping 적용까지 보유
  (`load_workflow_json` / `load_mapping_json` / `apply_mapping`, staticmethod). 현재 규모는 읽을 만함.
- 판단: 지금 분리하면 과설계. 다만 캐릭터/보이스 workflow까지 붙으면 이 파일이 금방 커짐.
- **분리 트리거**: 실제 배경 workflow JSON 교체 + 캐릭터/보이스 등 **두 번째 이상 workflow**가 추가될 때.
- **분리 방향(예시)**:
  ```text
  ai/comfy_client.py      # GET /system_stats, /object_info, health_check, is_available
  ai/workflow/loader.py   # workflow/mapping JSON 로드
  ai/workflow/mapper.py   # apply_mapping
  ai/image/background.py  # 배경 전용 조합 로직 (그대로)
  ```

---

## 2. 이미 관리됨 / 팀 결정 — 추가 조치 안 함

### 2.1 임시 `routers/ai_health.py` (`GET /api/ai/comfy-health`)
- 제거 시점·체크리스트는 [`TEMP_AI_CONNECTION_TEST.md`](TEMP_AI_CONNECTION_TEST.md)로 추적 중.
- **의존성 연결고리**: 이 임시 라우터가 `ai.comfy_client` → `httpx`를 끌어와 backend 런타임에 httpx 의존이 생겼다.
  그래서 `backend/requirements.txt`에 httpx를 넣었다.
  → **ai_health 제거 시 httpx가 여전히 필요한지 재검토**한다. (backend 본체는 httpx를 직접 쓰지 않음)

### 2.2 `backend/docs/` 가 Git ignored
- 루트 `.gitignore`의 `docs/` 규칙으로 `backend/docs/`가 무시됨 — **팀이 의도한 결정**(docs는 GitHub에 안 올림).
- 따라서 커밋되는 기준 문서는 **`backend/README.md`**(코드 변경 시 계속 갱신).
- 스펙/프롬프트 md는 로컬 작업 문서로만 유지.

### 2.3 `__pycache__/`, `.DS_Store`
- `.gitignore`로 차단됨. 무해. 별도 정리 불필요(원하면 로컬에서 삭제 가능).

---

## 3. 이번 리뷰에서 처리 완료 (참고)

- **stories.py 계층 통일**: `services/story_service.py` 신규, 라우터의 직접 `story_repository`/`HTTPException` 사용 제거,
  404 detail을 `"Story not found"`(`StoryNotFoundError`)로 통일 → 모든 라우터가 service + 공통 예외 패턴으로 일관.
- **requirements.txt ↔ pyproject 동기화**: httpx / websocket-client / pillow / python-multipart / `uvicorn[standard]` 반영 + 버전 핀.
  (source of truth는 pyproject.toml + uv.lock, requirements.txt는 pip 보조 목록)
- **(AI 리뷰) `apply_mapping` 마지막 path key 검증**: 마지막 key가 workflow에 없으면 `WorkflowMappingError`.
  (mapping 오타로 새 필드가 생기는 것 방지)
- **(AI 리뷰) timeout 양수 검증**: `COMFYUI_TIMEOUT_SECONDS`/생성자 인자가 `<= 0`이면 `ComfyUIConfigError`.
- **(AI 리뷰) `ai/image/__init__.py` 주석 최신화**: "background.py 미구현" → 실제(연결 준비 단계 구현됨) 반영.

### 검증 스냅샷
- import/라우트(25개) 정상
- stories parse / 목록 / 404(`"Story not found"`) 정상
- requirements.txt ↔ pyproject 의존성 일치
- AI: 배경 연결 테스트 통과, mapping 오타 차단 / timeout 0·음수 차단 확인

---

## 4. 커밋 주의 (구조와 직접 관련은 아니나 함께 점검)
- `main.py`가 `backgrounds`/`scenes` 라우터를 import하므로, 배경 기능 신규 파일들과 이를 참조하는 수정 파일은
  **한 커밋으로 원자적으로** 올린다. 일부만 커밋하면 `ModuleNotFoundError`로 import가 깨진다.

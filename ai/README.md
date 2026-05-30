# 몽실책방 AI 모듈

ComfyUI 연동 코드. **백엔드(FastAPI)와 분리된 독립 Python 모듈**이며 FastAPI에 의존하지 않는다.
HTTP 응답 변환은 backend 계층이 담당하고, 여기서는 순수 예외/함수만 제공한다.

## 구조

```text
ai/
├── comfy_client.py            # ComfyUIClient (조회 API + workflow/mapping 헬퍼)
├── core/exceptions.py         # AIError → ComfyUIError → (Config/Connection/Response/Timeout/WorkflowLoad/WorkflowMapping/BackgroundWorkflowPrepare)
├── image/
│   └── background.py          # 배경 생성 ComfyUI 연동 (연결 준비 단계)
├── workflows/
│   ├── background_generate.json          # 배경 workflow (현재 placeholder + TODO)
│   └── background_generate_mapping.json  # finalPrompt/negativePrompt 주입 위치 매핑
├── test_comfy_connection.py        # 공통 ComfyUI 연결 확인
└── test_background_connection.py   # 배경 연동 준비 확인
```

## 환경변수 (`ai/.env`)

`ai/.env.example`을 복사해 `ai/.env`를 만든다. (`ai/.env`는 gitignore)

| 변수 | 용도 |
|---|---|
| `COMFYUI_DEFAULT_URL` | 공통 ComfyUIClient 기본 URL |
| `COMFYUI_GPU1_URL` | **배경 생성용** ComfyUI (comfy1). `image/background.py`가 사용 |
| `COMFYUI_CHARACTER_URL` / `COMFYUI_VOICE_URL` | 캐릭터/보이스용 |
| `COMFYUI_TIMEOUT_SECONDS` | 요청 timeout (기본 10초) |

## 배경 생성 연동 — 현재 상태 (연결 준비 단계)

- 배경 생성 AI는 현재 **ComfyUI 연결 준비 단계**다. **실제 생성 완료 기능은 아직 구현하지 않았다.**
- 이미지 개수는 **코드가 아니라 ComfyUI workflow가 결정한다.** (코드에서 count/numImages/batch 강제 금지)
- AI 코드는 백엔드가 만든 `finalPrompt` / `negativePrompt`를 **그대로 받아 workflow에 주입**하는 역할만 한다. (프롬프트 작성자가 아니라 주입자)
- 배경은 **background only / no characters / no people / no animals**. 캐릭터 파이프라인과 혼동하지 않는다.
- 백엔드의 mock background generate 구조는 그대로 유지된다(후보 4장 mock은 백엔드 담당).

### `image/background.py` 함수
- `load_background_workflow()` / `load_background_mapping()` — workflow/mapping JSON 로드
- `build_background_workflow_payload(finalPrompt, negativePrompt)` — 주입 payload 준비
  - 현재 workflow가 placeholder면 주입을 보류하고 `{"workflowReady": False, ...}` 반환. 실제 workflow JSON으로 교체하면 자동으로 `workflowReady: True`로 주입된다.
- `prepare_background_generation(...)` — 위 함수의 별칭(준비까지만)
- `check_background_comfy_connection()` — 배경 ComfyUI 연결 확인 (읽기전용, **POST /prompt 호출 없음**)

### mapping JSON
`finalPrompt`/`negativePrompt`가 workflow의 어느 노드/경로에 들어가는지 정의한다.
workflow 구조가 바뀌어도 **코드 수정 없이 mapping JSON의 nodeId만** 바꾸면 된다.

```json
{
  "finalPrompt":    { "nodeId": "6", "path": ["inputs", "text"] },
  "negativePrompt": { "nodeId": "7", "path": ["inputs", "text"] }
}
```

## 실행 / 테스트

```bash
# 공통 연결 확인
uv run --env-file ai/.env python ai/test_comfy_connection.py

# 배경 연동 준비 확인 (base URL / 연결 / workflow·mapping 로드 / payload 구성 / 생성 미실행)
uv run --env-file ai/.env python ai/test_background_connection.py
```

> 두 테스트 모두 **실제 이미지를 생성하지 않는다.** `POST /prompt`를 호출하지 않고, 조회용 API(`/system_stats`, `/object_info`)만 사용한다.

## 아직 구현하지 않은 것
- 실제 배경 이미지 생성(`POST /prompt` 실행 / workflow 실행), 결과 이미지 수집/저장
- 실제 배경 workflow JSON (현재 placeholder)
- 캐릭터(`character_ctrl/`) / 보이스(`voice/`) / 비디오(`video/`)

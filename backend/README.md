# 몽실책방 백엔드

FastAPI 기반 백엔드 서버입니다.

## 가상환경 생성 및 패키지 설치

프로젝트 루트에서 `uv`를 사용합니다 (권장).

```bash
# 루트에서 실행
uv sync
```

`backend/` 폴더 안에서 직접 실행할 경우:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## 서버 실행

루트에서 uv를 사용하는 경우:

```bash
uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

`backend/` 폴더 안에서 직접 실행하는 경우:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 주요 URL

| 용도 | 주소 |
|---|---|
| Swagger 문서 | http://127.0.0.1:8000/docs |
| Health check | http://127.0.0.1:8000/api/health |
| 루트 | http://127.0.0.1:8000/ |

## 환경변수

`.env.example`을 복사해 `.env`를 만들고 필요한 값을 수정합니다.

```bash
cp .env.example .env
```

## 폴더 구조

```text
backend/
├── app/
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py          # GET /api/health
│   │   └── stories.py         # POST /api/stories/parse, GET /api/stories, GET /api/stories/{id}
│   ├── services/
│   │   ├── __init__.py
│   │   └── story_parser.py    # 빈 줄 기준 씬 분해, narration/dialogue 분리
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── story_repo.py      # 메모리 Mock Repository
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── story.py           # StoryParseRequest, StoryParseResponse 등
│   ├── storage/
│   │   └── .gitkeep           # 생성 결과물 저장 (git 제외)
│   ├── __init__.py
│   └── main.py
├── docs/
│   ├── backend_implementation_guide.md
│   ├── backend_health_api_setup_prompt.md
│   ├── backend_code_review_prompt.md
│   └── stories_parse_api_with_mock_prompt.md
├── .env.example
├── requirements.txt
└── README.md
```

## 구현된 API

| Method | Endpoint | 설명 |
|---|---|---|
| GET | `/` | 서비스 상태 확인 |
| GET | `/api/health` | 프론트-백엔드 연동 확인 |
| POST | `/api/stories/parse` | 대본을 씬으로 분해 후 메모리 저장 |
| GET | `/api/stories` | 저장된 스토리 목록 조회 |
| GET | `/api/stories/{story_id}` | 저장된 스토리 단건 조회 |

### 파싱 규칙

- 빈 줄(공백만 있는 줄 포함) 기준으로 씬 분리
- `화자: "대사"` 형식(큰따옴표 필수) → `dialogue`
- 그 외 모든 문장 → `narration`
- 형식이 맞지 않으면 에러 없이 `narration`으로 처리

### Mock Repository

- DB 없이 메모리 `dict`에 임시 저장
- storyId 자동 생성: `story_mock_001`, `story_mock_002`, ...
- 서버 재시작 시 데이터 초기화됨

## 추후 구현 예정

- `POST /api/characters` — 캐릭터 락 세트 저장
- `GET /api/characters` — 캐릭터 라이브러리 조회
- 배경 생성 / 캐릭터 누끼 / 레이어 합성 API
- ffmpeg 영상 렌더링 API
- 비동기 job 상태 관리

구현 순서는 `backend/docs/backend_implementation_guide.md` 15절을 참고합니다.

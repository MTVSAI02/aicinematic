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
│   │   └── health.py          # GET /api/health
│   ├── services/
│   │   └── __init__.py        # 추후 비즈니스 로직 구현
│   ├── repositories/
│   │   └── __init__.py        # 추후 저장소 레이어 구현
│   ├── schemas/
│   │   └── __init__.py        # 추후 Pydantic 스키마 정의
│   ├── storage/
│   │   └── .gitkeep           # 생성 결과물 저장 (git 제외)
│   ├── __init__.py
│   └── main.py
├── docs/
│   └── backend_implementation_guide.md
├── .env.example
├── requirements.txt
└── README.md
```

## 구현된 API

| Method | Endpoint | 설명 |
|---|---|---|
| GET | `/` | 서비스 상태 확인 |
| GET | `/api/health` | 프론트-백엔드 연동 확인 |

## 추후 구현 예정

아래 기능은 이번 단계에서 구현하지 않았습니다.

- `POST /api/stories/parse` — 대본 씬 분해
- `POST /api/characters` — 캐릭터 락 세트 저장
- `GET /api/characters` — 캐릭터 라이브러리 조회
- 배경 생성 / 캐릭터 누끼 / 레이어 합성 API
- ffmpeg 영상 렌더링 API
- 비동기 job 상태 관리

구현 순서는 `backend/docs/backend_implementation_guide.md` 15절을 참고합니다.

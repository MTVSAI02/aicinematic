# AI Cinematic

대본 → 씬 분해 → 캐릭터/배경 생성 → 합성 → 음성·영상 추출까지 이어지는 AI 영상 제작 도구.

- **frontend/** — React 19 + Vite 8 (UI)
- **backend/** — FastAPI (API 서버)
- **ai/** — ComfyUI·TTS 등 AI 엔진 연동 코드

---

## 요구 버전

| 항목 | 버전 | 관리 도구 |
|---|---|---|
| Python | 3.12+ | [uv](https://docs.astral.sh/uv/) |
| Node.js | 24 (LTS) | [nvm](https://github.com/nvm-sh/nvm) |
| npm | Node 24 동봉 | - |

> Node 버전은 [`.nvmrc`](.nvmrc), Python 버전은 [`.python-version`](.python-version) 에 고정돼 있습니다.

---

## 사전 설치 (각자 PC에 최초 1회)

### macOS / Linux / Git Bash

```bash
# uv (Python 패키지·가상환경 관리)
curl -LsSf https://astral.sh/uv/install.sh | sh

# nvm (Node 버전 관리)  — 이미 있으면 생략
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
```

### Windows (PowerShell)

```powershell
# uv
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# nvm-windows  (winget 으로 설치 / 또는 아래 GitHub 릴리스의 nvm-setup.exe)
winget install CoreyButler.NVMforWindows
#   https://github.com/coreybutler/nvm-windows/releases
```

> ⚠️ **Windows 의 nvm 은 별도 프로그램(nvm-windows)** 입니다. macOS 의 nvm 과 명령어가 살짝 다르고,
> **`.nvmrc` 를 자동으로 읽지 않습니다.** 그래서 아래에서 버전을 직접 적어줍니다 (`nvm install 24` / `nvm use 24`).
> 설치 후에는 **터미널을 새로 열어야** 인식됩니다.

설치 후 터미널을 새로 열어 `uv --version`, `nvm version`(Win) / `nvm --version`(mac) 이 나오면 OK.

---

## 처음 클론했을 때 (최초 세팅)

```bash
git clone <레포 주소> aicinematic
cd aicinematic
```

### 1) 백엔드 (Python / uv)

```bash
uv sync          # pyproject.toml + uv.lock 기준으로 .venv 자동 생성·동기화
```

> `uv sync` 한 번이면 끝. 가상환경(`.venv`)을 직접 만들거나 `pip install` 할 필요 없습니다.

### 2) 프론트 (Node / npm)

**macOS / Linux / Git Bash**
```bash
cd frontend
nvm install      # .nvmrc 보고 Node 24 설치 (최초 1회)
nvm use          # Node 24 로 전환 (터미널 새로 열 때마다)
npm install      # package-lock.json 기준으로 동일 버전 설치
cp .env.example .env   # 환경변수 파일 생성 (필요시 값 수정)
```

**Windows (PowerShell)**
```powershell
cd frontend
nvm install 24         # Node 24 설치 (최초 1회) — nvm-windows 는 버전 직접 지정
nvm use 24             # Node 24 로 전환
npm install            # package-lock.json 기준으로 동일 버전 설치
Copy-Item .env.example .env   # 환경변수 파일 생성 (필요시 값 수정)
```

**Windows (cmd)**
```bat
cd frontend
nvm install 24
nvm use 24
npm install
copy .env.example .env
```

---

## 실행

### 프론트 개발 서버
```bash
cd frontend
nvm use          # Node 24 확인  (Windows: nvm use 24)
npm run dev      # http://localhost:5173
```

### 백엔드 서버
```bash
uv run uvicorn backend.app.main:app --reload   # http://localhost:8000
```
> API 자동 문서: http://localhost:8000/docs

---

## 연동 확인 (셋업 검증) ✅

**프론트 + 백엔드가 서로 연결돼야 환경설정이 제대로 끝난 것**입니다. 아래로 확인하세요.

1. 터미널 2개를 열어 **백엔드와 프론트 서버를 둘 다** 실행한다. (위 [실행](#실행) 참고)
2. 브라우저에서 **http://localhost:5173** 접속.
3. 화면에 **`✅ 백엔드 연결 성공`** 과 응답 JSON `{"status":"ok",...}` 이 보이면 정상.

브라우저 없이 터미널로만 확인하려면:
```bash
curl http://localhost:8000/api/health
# → {"status":"ok","service":"ai-cinematic-backend"}
```

### ❌ `백엔드 연결 실패` 가 뜨면

| 원인 | 해결 |
|---|---|
| 백엔드 서버가 안 켜짐 | `uv run uvicorn backend.app.main:app --reload` 실행했는지 확인 |
| 주소가 다름 | `frontend/.env` 의 `VITE_API_BASE_URL` 이 백엔드 주소(`http://localhost:8000`)와 같은지 확인 |
| `.env` 가 없음 | `cp .env.example .env` (Windows: `copy` / `Copy-Item`) 했는지 확인 |
| `.env` 수정 후 반영 안 됨 | `.env` 는 **서버 재시작해야** 적용됨 → 프론트 `npm run dev` 끄고 다시 실행 |
| CORS 에러 (콘솔 빨간 메시지) | 백엔드 `main.py` 의 `allow_origins` 에 프론트 주소가 있는지 확인 |

---

## 매번 `git pull` 받은 뒤 (싱크 맞추기)

다른 사람이 패키지를 추가했을 수 있으니, pull 후 아래를 실행하세요.

```bash
uv sync           # 백엔드 의존성 동기화
cd frontend
npm install       # 프론트 의존성 동기화
```

> Windows PowerShell 5.1 은 `&&` 가 안 되니 위처럼 줄을 나눠 실행하세요. (cmd / PowerShell 7+ 는 `&&` 가능)

- `uv.lock` 이 바뀌었으면 → `uv sync`
- `frontend/package-lock.json` 이 바뀌었으면 → `npm install`
- `.nvmrc` 가 바뀌었으면 → mac: `nvm install && nvm use` / Windows: `nvm install 24 && nvm use 24`

---

## 패키지 추가할 때 (★ lock 파일 함께 커밋)

직접 `requirements.txt`/`package.json` 을 손으로 고치지 말고 명령어로 추가하세요.
lock 파일이 자동 갱신되며, **바뀐 lock 파일을 꼭 같이 커밋**해야 팀원 환경이 동일해집니다.

```bash
# 백엔드 패키지 추가
uv add <패키지명>            # 예: uv add pydantic
#   → pyproject.toml + uv.lock 갱신됨 → 둘 다 커밋

# 프론트 패키지 추가
cd frontend
npm install <패키지명>       # 예: npm install zustand
#   → package.json + package-lock.json 갱신됨 → 둘 다 커밋
```

---

## 환경변수

- `frontend/.env` 는 **git 에 올라가지 않습니다**(`.gitignore` 처리).
- 새로 받은 사람은 [`frontend/.env.example`](frontend/.env.example) 을 복사해서 `.env` 를 만드세요.
- 새 환경변수가 생기면 `.env.example` 에도 추가해서 팀에 공유하세요.

| 변수 | 설명 | 예시 |
|---|---|---|
| `VITE_API_BASE_URL` | 백엔드 주소 | `http://localhost:8000` |

---

## 폴더 구조

```
aicinematic/
├── frontend/          # React + Vite
│   └── src/
│       ├── pages/     # 화면 단위 (담당 분리)
│       ├── components/api/store/
├── backend/           # FastAPI
│   └── app/{routers,services,repositories,schemas,storage}/
├── ai/                # AI 엔진 연동: comfy_client(ComfyUI), image/배경, workflows, ... → ai/README.md
├── pyproject.toml     # 백엔드 의존성 (uv)
├── uv.lock
└── .nvmrc / .python-version
```

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

`backend/.env`(gitignore)에 앱/ComfyUI 설정을 둔다. **`backend/.env`는 선택사항** — 없으면
`main.py`가 자동으로 `ai/.env`로 fallback하므로, ComfyUI 값만 `ai/.env`에 있으면 그대로 동작한다.

`backend/.env`를 따로 쓰려면 아래 변수를 채운다. (값은 코드/문서에 하드코딩하지 않고 `.env`에만 둔다. ComfyUI 서버 주소는 팀에서 공유)

| 변수 | 용도 |
|---|---|
| `APP_NAME` / `APP_ENV` / `FRONTEND_URL` / `STORAGE_DIR` | 앱 기본 설정 |
| `AI_SERVER_URL` | **우리 AI FastAPI 서버** 주소 (배경 생성 `/generate` 호출용). 예: `http://192.168.0.35:5000` |
| `COMFYUI_DEFAULT_URL` | ComfyUIClient 기본 URL (캐릭터 in-process 생성용) |
| `COMFYUI_CHARACTER_URL` | 캐릭터 생성용 ComfyUI |
| `COMFYUI_TIMEOUT_SECONDS` | 요청 timeout(초) |

> 로드 우선순위: `backend/.env` → 없으면 `ai/.env`. (`main.py`의 `_load_env`)

## 폴더 구조

```text
backend/
├── app/
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py          # GET /api/health
│   │   ├── stories.py         # POST /api/stories/parse, GET /api/stories, GET /api/stories/{id}, PATCH .../narrator-voice
│   │   ├── characters.py      # POST /api/characters/generate, 캐릭터 CRUD
│   │   ├── jobs.py            # GET /api/jobs/{job_id}
│   │   ├── backgrounds.py     # 배경 프롬프트 추천/생성 Job/라이브러리 CRUD
│   │   ├── scenes.py          # 씬-배경 연결(PATCH .../background) + 씬-캐릭터(PATCH 추가/수정, DELETE 제거; 다중)
│   │   ├── tts.py             # POST /api/tts/scene, GET /api/tts, DELETE /api/tts/{audio_id}
│   │   └── voices.py          # 보이스 라이브러리 CRUD + PATCH /api/characters/{id}/voice는 characters.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── story_parser.py    # 빈 줄 기준 씬 분해, narration/dialogue 분리 + 감정 태그/키워드
│   │   ├── story_service.py   # 스토리 파싱/저장/조회 (StoryNotFoundError)
│   │   ├── job_manager.py     # InMemoryJobManager: run_async(비동기,ThreadPool)/run(동기). 나중에 RabbitMQ/Celery로 교체
│   │   ├── character_service.py  # 캐릭터 CRUD 비즈니스 로직 (커스텀 예외 발생)
│   │   ├── job_service.py     # Job 조회 비즈니스 로직 (JobNotFoundError)
│   │   ├── background_service.py  # 배경 추천/라이브러리 CRUD/씬 연결 + 프롬프트 규칙
│   │   ├── tts_service.py     # scene.items → TTS audio target 생성/조회/삭제 (speaker→voiceId 반영)
│   │   └── voice_service.py   # 보이스 라이브러리 CRUD (삭제 시 캐릭터 voiceId 캐스케이드)
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── story_repo.py      # 메모리 Mock Repository
│   │   ├── character_repo.py  # 캐릭터 메모리 Mock Repository
│   │   ├── job_repo.py        # Job 상태 메모리 Mock Repository
│   │   ├── background_candidate_repository.py  # 배경 후보(임시) 메모리 저장
│   │   ├── background_repository.py            # 배경 라이브러리 메모리 저장
│   │   ├── tts_audio_repository.py             # TTS audio 메타 메모리 저장
│   │   └── voice_repository.py                 # 보이스 라이브러리 메모리 저장
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── story.py           # StoryParseRequest, StoryParseResponse (scene backgroundId/emotion 포함)
│   │   ├── character.py       # Character 요청/응답 모델
│   │   ├── job.py             # JobStatus/JobType Enum, JobResponse, JobCreatedResponse
│   │   ├── background.py      # Background 후보/라이브러리/씬연결 모델
│   │   ├── tts.py             # TTS 생성 요청/audio 응답/삭제 응답 모델
│   │   └── voice.py           # Voice 생성/수정/응답/삭제 모델
│   ├── core/
│   │   ├── __init__.py
│   │   ├── exceptions.py          # AppException 및 커스텀 예외
│   │   └── exception_handlers.py  # AppException → HTTP 응답 변환 핸들러
│   ├── storage/
│   │   └── .gitkeep           # 생성 결과물 저장 (git 제외)
│   ├── __init__.py
│   └── main.py
├── docs/
│   ├── backend_implementation_guide.md
│   ├── backend_health_api_setup_prompt.md
│   ├── backend_code_review_prompt.md
│   └── stories_parse_api_with_mock_prompt.md
├── .env                  # 로컬 환경변수(gitignore). 없으면 ai/.env 로 fallback
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
| PATCH | `/api/stories/{story_id}/narrator-voice` | 나레이션 보이스 연결/해제 (body: voiceId, null이면 해제) |
| POST | `/api/characters/generate` | 캐릭터 생성 Job 요청 (**비동기** → `pending` 반환, 폴링) |
| GET | `/api/jobs/{job_id}` | Job 상태 조회 (character_generate / background_generate / tts_generate) |
| GET | `/api/characters` | 캐릭터 목록 조회 |
| POST | `/api/characters` | 캐릭터 결과 직접 저장 |
| GET | `/api/characters/{character_id}` | 캐릭터 단건 조회 |
| PATCH | `/api/characters/{character_id}` | 캐릭터 부분 수정 (name/appearancePrompt/imageUrl) |
| DELETE | `/api/characters/{character_id}` | 캐릭터 삭제 |
| POST | `/api/backgrounds/prompt-suggestions` | 씬 기반 배경 프롬프트 추천 (이미지 생성 X) |
| POST | `/api/backgrounds/generate` | 배경 후보 생성 Job (**비동기** → `pending` 반환, 폴링; body `{prompt}`만). Backend→AI 서버(/generate)→ComfyUI |
| POST | `/api/backgrounds` | 후보 1장 → 배경 라이브러리 저장 |
| GET | `/api/backgrounds` | 저장된 배경 목록 조회 |
| GET | `/api/backgrounds/{background_id}` | 저장된 배경 단건 조회 |
| PATCH | `/api/backgrounds/{background_id}` | 배경 수정 (name만) |
| DELETE | `/api/backgrounds/{background_id}` | 배경 삭제 (+참조 씬 backgroundId null) |
| PATCH | `/api/scenes/{scene_id}/background` | 씬에 배경 연결 (body: storyId, backgroundId) |

| POST | `/api/tts/scene` | 씬 TTS 생성 Job (`AI_TTS_URL`/`QWEN_TTS_ENABLED` 설정 시 실제 합성, 미설정 시 audioUrl=null) |
| PATCH | `/api/scenes/{scene_id}/character` | 씬에 캐릭터 추가/수정 (**씬당 다중**; body: storyId, characterId, sceneAppearancePrompt?) |
| DELETE | `/api/scenes/{scene_id}/character/{character_id}` | 씬에서 캐릭터 1명 제거 (query: storyId) |

| GET | `/api/tts?storyId=&sceneId=` | 씬별 TTS 결과 목록 조회 |
| DELETE | `/api/tts/{audio_id}` | TTS 결과 삭제 |
| POST | `/api/voices` | 보이스 자산 생성 (mock) |
| GET | `/api/voices` | 보이스 라이브러리 목록 |
| GET | `/api/voices/{voice_id}` | 보이스 단건 조회 |
| PATCH | `/api/voices/{voice_id}` | 보이스 수정 |
| DELETE | `/api/voices/{voice_id}` | 보이스 삭제 (+참조 캐릭터 voiceId null) |
| PATCH | `/api/characters/{character_id}/voice` | 캐릭터에 보이스 연결 (body: voiceId) |

### 파싱 규칙

- 빈 줄(공백만 있는 줄 포함) 기준으로 씬 분리
- `화자: "대사"` 형식(큰따옴표 필수) → `dialogue`
- 그 외 모든 문장 → `narration`
- 형식이 맞지 않으면 에러 없이 `narration`으로 처리

#### 감정 태그 (선택)

각 줄 맨 앞에 선택적으로 `[감정]` 태그를 붙일 수 있다. 결과 item에 `emotion`(영문 키) + `emotionLabel`(한글)이 **항상** 포함된다.

```text
[화남] 어린왕자: "싫어"   → dialogue, emotion=angry, emotionLabel=화남
[잔잔함] 어린 왕자는 …   → narration, emotion=calm, emotionLabel=잔잔함
```

- **지원 감정**: 기본(neutral) · 잔잔함(calm) · 기쁨(happy) · 슬픔(sad) · 화남(angry) · 무서움(scared) · 신남(excited) · 다정함(friendly) · 진지함(serious)

**emotion 결정 우선순위**
1. 지원하는 `[감정]` 태그가 있으면 → 그 감정 (명시 우선)
2. **태그가 없을 때만** 본문 키워드로 추정 (규칙 기반, 아래 표)
3. 그래도 못 정하면 → 타입별 기본값: narration=`calm/잔잔함`, dialogue=`neutral/기본`

| emotion | 본문 키워드 |
|---|---|
| happy | 하하, 기뻐, 좋아, 웃음, 웃었, 웃어 |
| scared | 무서워, 무서웠, 두려워, 떨었, 벌벌, 덜덜 |
| sad | 슬퍼, 슬펐다, 눈물, 울었다, 울었어, 울고 |
| angry | 화가, 화났, 싫어, 싫었, 짜증 |
| friendly | 안녕, 반가워, 반가웠 |
| calm | 조용히, 천천히, 별빛, 고요 |

- 키워드 추정은 **부분 문자열 매칭**이라, 1글자/모호 키워드는 오탐을 만든다(예: `울`→"서울/울산/울타리", `떨`→"떨어지다"). 그래서 **명확한 표현만** 사용한다(`울` 대신 `울었다`/`눈물` 등). 정답이 아니라 **추정**이며, `[감정]` 태그로 언제든 덮어쓸 수 있다(정밀화는 추후 LLM).
- **태그가 있으면(유효/무효 무관) 키워드 추정은 하지 않는다.** 미지원 태그(예: `[짜증]`)는 그대로 제거되고 타입 기본값이 적용된다.
- 줄 맨 앞의 `[...]`는 **항상 감정 태그로 인식**해 제거한다. → 나레이션에서 대괄호를 본문 그대로 쓰려면 맨 앞에 두지 말 것.
- 라벨 앞뒤 공백 허용(`[ 화남 ]` = `[화남]`). 태그를 떼고 본문이 비면(`[화남]`만 있는 줄) 해당 줄은 item을 만들지 않고 스킵한다.

### Mock Repository

- DB 없이 메모리 `dict`에 임시 저장
- storyId 자동 생성: `story_mock_001`, `story_mock_002`, ...
- characterId 자동 생성: `char_mock_001`, `char_mock_002`, ...
- jobId 자동 생성: `job_mock_001`, `job_mock_002`, ...
- backgroundId 자동 생성: `bg_mock_001`, ...  / 배경 후보: `bg_candidate_001`, ...
- audioId 자동 생성(TTS): `audio_mock_001`, ...
- 서버 재시작 시 데이터 초기화됨

### Voice(보이스) API — 캐릭터·나레이션 목소리 자산

보이스는 캐릭터/배경처럼 **재사용 가능한 라이브러리 자산**이다. 보이스를 만들어 `voiceId`를 발급하고, 캐릭터(`character.voiceId`)와 스토리 나레이션(`story.narratorVoiceId`)이 그 `voiceId`를 참조한다.

```text
Voice 라이브러리 → voiceId 발급
  ├─ 캐릭터에 연결(character.voiceId)        → TTS가 dialogue speaker로 캐릭터를 찾아 voiceId 사용
  └─ 스토리에 연결(story.narratorVoiceId)    → TTS가 narration item에 voiceId 사용
기본 나레이터 보이스 4개는 서버 시작 시 preset으로 seed된다(아래 표).
```

- **백엔드/AI 역할 분리 (중요)**: 백엔드는 **자산 정체성·참조**만 관리한다.
  - **생성 요청(`POST /api/voices`)은 `name`(필수) + `description`/`voicePrompt`(선택)만 받는다.**
  - `provider`/`model`/`sampleAudioUrl`/`status`는 **"실제 목소리를 어떻게 만드는가"**라 **AI/TTS 파트(김도연)가 채우는 결과 필드**다. 백엔드의 **생성(POST)·수정(PATCH) 어느 쪽도 이 필드를 받지 않는다.** (캐릭터에서 seed/style/model을 백엔드가 받지 않는 것과 동일 원칙) 그중 `provider`/`model`은 사용자 화면에 불필요해 **응답에서도 제외**(내부 보관만), `sampleAudioUrl`/`status`는 미리듣기·선택 가능 여부 판단에 필요해 응답에 포함한다.
  - **자산 구분 필드**: `voiceType`(narrator/character, 추천 용도) + `isPreset`(시스템 기본 보이스 여부). 사용자 생성 보이스는 `voiceType="character"`, `isPreset=false`.
  - 생성 직후 `status="pending"`(AI 클로닝 대기). 실제 클로닝 결과(provider/model/sampleAudioUrl/status)는 **AI 통합 단계에서 AI 파트가 채운다** — 현재 백엔드엔 그 통로가 없다(TTS `audioUrl`을 백엔드가 채우지 않는 것과 동일).
  - **수정(`PATCH /api/voices/{id}`)은 사용자 메타(`name`/`description`/`voicePrompt`)만** 바꾼다.
  - **삭제(`DELETE /api/voices/{id}`)**: 보이스 제거 + 참조 캐릭터 `voiceId`·스토리 `narratorVoiceId` null 캐스케이드(AI 무관).
- **캐릭터 연결**: `PATCH /api/characters/{id}/voice` body `{"voiceId": "voice_mock_001"}` (null이면 해제). 연결 시 보이스 존재 검증(없으면 404) + **`voiceType="character"` 검증**(아니면 400, narrator preset을 캐릭터에 못 붙임).
- **나레이터 연결**: `PATCH /api/stories/{storyId}/narrator-voice` body `{"voiceId": "voice_preset_narrator_calm_001"}` (null이면 해제). 연결 시 보이스 존재 검증(없으면 404), 없는 스토리면 404. **`voiceType="narrator"`인 보이스만 연결 가능**(character 타입이면 400 Invalid narrator voice) — 즉 현재는 preset 4개만 narrator로 붙는다. (narration은 화자가 없어 캐릭터로 못 붙이므로 story 단위로 둠)
- **삭제 캐스케이드**: 보이스 삭제 시 그 `voiceId`를 참조하던 **모든 캐릭터의 `voiceId`**와 **스토리의 `narratorVoiceId`**를 null로 만든다(배경 삭제와 동일 정책).
- **TTS 반영(dialogue)**: dialogue의 `speaker`로 저장된 캐릭터(name 매칭)를 찾아 그 `characterId`/`voiceId`를 audio에 복사. 매칭 캐릭터가 없으면 null. (목소리=character.voiceId 고정, 감정=item.emotion 문장별)
- **TTS 반영(narration)**: narration은 audio의 voiceId로 **story.`narratorVoiceId`**를 복사한다. 미설정이면 null.

**기본 나레이션 보이스 (preset 4개, 메모리 seed)**

narration은 화자가 없어 캐릭터로 목소리를 못 붙이므로, 사용자가 바로 고를 수 있는 **기본 나레이터 보이스 4개**를 서버 시작 시 메모리에 seed한다(고정 ID라 재시작/생성 순서와 무관하게 같은 ID로 참조). `GET /api/voices`에 사용자 보이스와 함께 반환되며, 프론트는 `voiceType=="narrator" && isPreset==true`로 골라 "기본 나레이션" 섹션에 보여준다.

| voiceId | 이름 |
|---|---|
| `voice_preset_narrator_calm_001` | 차분한 나레이션 |
| `voice_preset_narrator_bright_001` | 밝은 나레이션 |
| `voice_preset_narrator_soft_001` | 부드러운 나레이션 |
| `voice_preset_narrator_serious_001` | 진지한 나레이션 |

- preset은 `voiceType="narrator"`, `isPreset=true`, `status="ready"`, `sampleAudioUrl=null`로 seed된다.
- **선택은 가능(status=ready)하지만 미리듣기 샘플(`sampleAudioUrl`)은 아직 null** — 실제 샘플 음성 생성은 AI/TTS 파트 몫(채워지면 프론트 미리듣기 버튼 활성화).
- **보호 정책**: preset(`isPreset=true`)은 **수정·삭제 불가**. `PATCH` → 400(Default voice cannot be modified), `DELETE` → 400(Default voice cannot be deleted).

**생성 요청 (백엔드가 받는 것)**

```json
{ "name": "따뜻한 소년 목소리", "description": "밝고 호기심 많은 톤", "voicePrompt": "warm curious boy voice" }
```

**생성 직후 응답 (사용자 생성 → voiceType=character, isPreset=false)**

```json
{
  "voiceId": "voice_mock_001", "name": "따뜻한 소년 목소리",
  "description": "밝고 호기심 많은 톤", "voicePrompt": "warm curious boy voice",
  "voiceType": "character", "isPreset": false, "status": "pending", "sampleAudioUrl": null
}
```

> `provider`/`model`은 AI/TTS 내부 메타라 **응답에 노출하지 않는다**(내부 repository엔 보관). 사용자 보이스 선택 화면엔 불필요하기 때문.

### TTS(음성 생성) API

TTS는 **scene 단위**로 생성한다. 이미 파싱된 `scene.items`(text/emotion/speaker)를 그대로 사용하고, 백엔드가 `audioId`를 먼저 발급한 뒤 `TTS_AI_CONTRACT.md` 형태로 AI/TTS에 전달한다. `AI_TTS_URL`이 있으면 원격 AI/TTS 서버를 호출하고, `QWEN_TTS_ENABLED=1`이면 로컬 Qwen3-TTS 어댑터를 사용한다. 둘 다 없으면 기존처럼 `audioUrl=null` 메타만 만든다.

> #### 📍 현재 단계 (중요): "백엔드 mock 구조"까지만
>
> ```text
> [프론트] ──▶ [백엔드 TTS API] ──▶ [`AI_TTS_URL` 원격 TTS 또는 로컬 Qwen3-TTS] ──▶ [audioId별 audioUrl/durationSec/error]
> ```
>
> - ✅ **됨**: 백엔드 TTS API (scene.items → audio target 생성/저장/조회/삭제, `tts_generate` Job). AI/TTS 설정이 없으면 `audioUrl=null` 메타를 반환한다.
> - ✅ **됨 (AI 요청)**: `AI_TTS_URL` 설정 시 `POST {AI_TTS_URL}/tts`, `QWEN_TTS_ENABLED=1` 설정 시 로컬 Qwen3-TTS로 실제 wav 생성. 미설정이면 `audioUrl=null`로 계약 메타만 저장한다.
> - ✅ **됨 (프론트 연동)**: `frontend/src/api/voiceApi.js`가 `/api/tts/scene` Job을 만들고 `/api/jobs/{jobId}`를 polling한 뒤 `audioUrl`을 재생한다.
> - ✅ **됨**: character voice 매핑(dialogue `speaker` → 저장 캐릭터(name 매칭) → `characterId`/`voiceId`를 audio에 복사). 보이스 라이브러리(`/api/voices`) + 캐릭터 연결(`PATCH /api/characters/{id}/voice`)도 구현됨.
> - ❌ **안 됨**: 보이스 클로닝(voiceId에 실제 목소리 매핑 = provider/model/sampleAudioUrl/status 채우기)은 AI/TTS 파트 영역.
>
> 즉 이번 단계는 캐릭터/배경 때와 동일하게 **"구조·흐름만 먼저, 실제 AI·프론트 연동은 다음 단계"** 다.
>
> **백엔드 ↔ AI/TTS 요청·응답 JSON 계약**(팀원 전달용): 루트 [`TTS_AI_CONTRACT.md`](../TTS_AI_CONTRACT.md)


- **AI/TTS 호출 방식**: `AI_TTS_URL` 우선, 없으면 `QWEN_TTS_ENABLED=1`일 때 로컬 Qwen3-TTS, 둘 다 없으면 `audioUrl=null`. `tts_generate` Job은 현재 즉시 `completed`이며 결과에 `audios` 배열을 담는다.

- **감정은 그대로 통과**: TTS가 감정을 새로 판단하지 않고 `item.emotion`/`emotionLabel`을 복사한다. (감정 결정은 Story Parse 책임)
- **voiceType / voiceId**: narration→`narrator`, dialogue→`character`.
  - **dialogue**: `speaker`로 저장 캐릭터(name 매칭)를 찾아 그 `characterId`/`voiceId`를 복사. 매칭 캐릭터 없거나 보이스 미연결이면 null.
  - **narration**: `characterId`는 항상 null, `voiceId`는 story.`narratorVoiceId` 복사(미설정이면 null).
  - 방향: **목소리=voiceId(캐릭터/나레이터 고정), 감정=item.emotion(문장별)**. (실제 합성/클로닝은 AI 파트 → `audioUrl`은 여전히 null)
- **itemIndex**: `scene.items`의 **원본 index 유지**. (방어적으로 text 빈 item을 제외해도 재번호하지 않음 → 프론트가 원본 item과 audio를 정확히 매칭)
- **재생성 = 교체**: 같은 `storyId`+`sceneId`로 다시 생성하면 **기존 audio를 삭제하고 새 결과로 교체**(누적 X). 스토리 text/emotion 수정 시 이전 오디오 혼란 방지.
- **빈 처리**: text 빈 item은 audio 대상에서 제외하고, 생성할 item이 하나도 없으면 `EmptySceneItemsError(400)`.
- **조회/생성 검증 차이**: `POST /api/tts/scene`은 story/scene을 검증(없으면 404). `GET /api/tts`는 저장소 조회라 검증 없이 없으면 빈 배열 `[]`.

**TTSAudio 구조**

```json
{
  "audioId": "audio_mock_001", "storyId": "story_mock_001", "sceneId": "scene_001",
  "itemIndex": 0, "type": "narration", "speaker": null, "text": "...",
  "emotion": "calm", "emotionLabel": "잔잔함",
  "voiceType": "narrator", "characterId": null, "voiceId": null, "audioUrl": null
}
```

### 배경(Background) API

배경은 캐릭터와 달리 **생성 결과를 바로 저장하지 않는다.** 후보 4장 중 1장을 골라 저장한다.

```text
프롬프트 추천 → 후보 4장 생성(Job) → [후보 임시] → 1장 선택 저장 → [배경 라이브러리] ← 씬은 backgroundId만 참조
```

- **2단계 저장소**: 후보(`bg_candidate_*`, 임시) → 선택 저장(`bg_mock_*`, 라이브러리)
- 배경은 특정 씬 소유물이 아니라 **여러 스토리/씬에서 재사용**하는 자산. 씬은 `backgroundId`만 참조한다(candidateId 직접 연결 금지).
- **프롬프트 규칙(LLM 전, 규칙 기반)**: `finalPrompt = {prompt}, storybook background, soft painterly style, clean composition, background only, no characters`. → 배경엔 사람/동물 금지(캐릭터는 별도 라이브러리). **negativePrompt는 backend가 다루지 않는다**(AI 서버/ComfyUI 워크플로 내부 고정값).
- **⚠️ generate `prompt` 계약**: `POST /api/backgrounds/generate`의 `prompt`는 **맨 프롬프트**(suggestedPrompt 또는 사용자가 수정한 원본)여야 한다. suffix가 붙은 `finalPrompt`를 보내면 중복된다. **finalPrompt 조립은 백엔드 책임**. → 프론트는 `promptInput`(전송용)과 `finalPromptPreview`(표시용) 상태를 분리하고, `generateBackground({ prompt })`에 finalPrompt를 넣지 않는다. (가드는 두지 않고 계약으로 관리. 실수가 반복되면 "prompt에 backend suffix 포함 시 422"로 막는 방향 검토)
- **suggestedPrompt**: scene.items의 narration(없으면 dialogue) → sourceText → 키워드 사전(사막/별빛/숲/바다…) 매칭, 없으면 기본값. **정답이 아니라 초안**이며 사용자가 수정.
- **수정**: MVP는 `name`만. **삭제**: 참조하던 모든 scene의 backgroundId를 null로 정리.
- **생성 구조 (AI FastAPI 서버 경유)**: `Backend → 우리 AI 서버(/generate) → 외부 ComfyUI`. **Backend는 ComfyUI를 직접 호출하지 않는다.**
  - Backend는 finalPrompt를 만들어 AI 서버에 **`{ "prompt": finalPrompt }`만** 보낸다(필드명 항상 `prompt`).
  - AI 서버는 **1회 호출로 ComfyUI batch 결과(여러 장)** 를 `{ "images": ["<base64 png>", ...] }`로 반환. **후보 개수는 AI/ComfyUI가 결정**(백엔드는 받은 만큼 저장).
  - Backend가 각 base64를 디코드해 `storage/backgrounds/candidates/{candidateId}.png`로 저장, `imageUrl` 생성.
  - AI 서버 주소는 `AI_SERVER_URL`(env). 연결/응답 실패 시 **mock fallback 없이 Job `failed`**(원인을 `error`에 보존).
- **Job**: `JobType.background_generate`로 `InMemoryJobManager.run_async`(비동기). `pending` 반환 후 폴링(캐릭터와 동일). 저장 책임은 backend(이미지 저장/imageUrl/repository).
- scene 응답에 `backgroundId`(optional, 기본 null) 포함.

### 캐릭터 / Job API

캐릭터는 **재사용**을 위해 라이브러리에 저장된다. 한 번 만든 캐릭터를 다른 스토리에서도 다시 불러와 사용할 수 있다.

**캐릭터 데이터 구조**

```json
{
  "characterId": "char_mock_001",
  "name": "어린왕자",
  "appearancePrompt": "금발 단발, 초록 외투를 입은 작은 소년",
  "description": "호기심 많고 다정한 어린 왕자",
  "imageUrl": "/storage/characters/char_mock_001.png",
  "voiceId": null
}
```

- `description`은 optional(nullable). 저장/표시용 메타데이터로, 생성 prompt에는 `appearancePrompt`만 쓰인다.
- `imageUrl`은 optional(nullable). 생성 성공 시 backend가 bytes를 `storage/characters/{characterId}.png`로 저장하고 경로를 채운다(생성 전/실패 시 `null`).
- `voiceId`는 연결된 보이스 자산(기본 `null`). `PATCH /api/characters/{id}/voice`로 연결/해제한다.
- PATCH 동작 기준 (나중에 DB 컬럼 nullability와 1:1 매핑):
  - `imageUrl`: nullable → `PATCH {"imageUrl": null}`을 보내면 **실제로 `null`로 초기화**된다(이미지 연결 해제).
  - `name` / `appearancePrompt`: NOT NULL 성격 → 명시적 `null`을 보내면 무시되고 기존 값이 유지된다(공백 문자열은 `422`).
  - 라우터에서 `exclude_unset`으로 "미전달"과 "명시적 null"을 구분한다.

**Job 데이터 구조**

```json
{
  "jobId": "job_mock_001",
  "type": "character_generate",
  "status": "completed",
  "progress": 100,
  "result": { "characterId": "char_mock_001", "name": "어린왕자", "appearancePrompt": "...", "imageUrl": null },
  "error": null
}
```

- `status`는 `JobStatus` Enum으로 제한: `pending`, `running`, `completed`, `failed`
- 캐릭터 생성은 비동기 Job 구조로, `POST /api/characters/generate`가 `jobId`를 반환하고 클라이언트가 `GET /api/jobs/{job_id}`로 상태를 폴링한다.

**현재 구현 범위 / 가정**

- **ComfyUI 실제 생성으로 전환됨.** 캐릭터 생성은 `InMemoryJobManager.run_async`로 **비동기** 처리한다 — `pending`을 즉시 반환하고 백그라운드(ThreadPoolExecutor)에서 ComfyUI를 호출한다. (생성 실패 시 캐릭터 레코드 미저장 = orphan 방지)
- RabbitMQ/Celery는 아직 아님. **MVP는 in-memory ThreadPoolExecutor** — 서버 재시작 시 pending/running Job은 유실된다. 배포 단계에서 Redis Queue/Celery/RQ로 교체(이 클래스만 publish 버전으로).
  - 현재: `FastAPI → InMemoryJobManager.run_async(ThreadPool) → ComfyUI → Character Result`
  - 나중: `FastAPI → RabbitMQ/Celery → Worker → ComfyUI → Character Result`
- async/sync 정책은 아래 "비동기 Job / 저장 구조" 섹션 참고.
- 스타일(`stylePreset`) / `seed` / `referenceImageUrl` / `lockProfile`은 백엔드가 받지 않는다. 스타일·seed·캐릭터 고정은 ComfyUI 파트에서 관리한다고 가정한다.
- 캐릭터는 `voiceId`(연결된 보이스 자산, 기본 null)를 가진다. 연결은 `PATCH /api/characters/{id}/voice`로 하며, 실제 목소리 클로닝/합성은 AI/TTS 파트가 담당한다. (보이스 라이브러리는 "Voice(보이스) API" 참고)

**예외 처리 기준**

| 상황 | 응답 |
|---|---|
| 존재하지 않는 `character_id` 조회/수정/삭제 | `404 {"detail": "Character not found"}` |
| 존재하지 않는 `job_id` 조회 | `404 {"detail": "Job not found"}` |
| PATCH에 수정 가능한 필드가 하나도 없음 | `400 {"detail": "No fields to update"}` |
| `name`/`appearancePrompt` 누락·비문자열·빈 문자열·공백만 | `422` validation error |
| Job 처리 중 예외 발생 | Job `status=failed`, `progress=0`, `result=null`, `error="Character generation failed"` 저장 (`GET /api/jobs/{id}`로 확인) |

**예외 처리 공통 구조 (계층 분리)**

예외 처리는 `core/exceptions.py`와 `core/exception_handlers.py`로 공통 관리한다.

```text
repository  → 저장/조회/수정/삭제 결과만 반환. 없으면 None/False. FastAPI(HTTPException)에 의존하지 않음
service     → 비즈니스 예외 판단. CharacterNotFoundError, JobNotFoundError, NoFieldsToUpdateError 등 커스텀 예외 발생
router      → request 수신 → service 호출 → 응답 반환. HTTPException을 직접 던지지 않음
global handler → main.py에 등록된 app_exception_handler가 AppException을 HTTP 응답({"detail": ...})으로 변환
```

- 커스텀 예외는 `AppException`을 상속하며 `status_code`/`detail`을 가진다.
  - 캐릭터/Job: `CharacterNotFoundError` (404), `JobNotFoundError` (404), `NoFieldsToUpdateError` (400), `CharacterGenerationFailedError` (500)
  - 배경/씬: `BackgroundCandidateNotFoundError` (404), `BackgroundNotFoundError` (404), `BackgroundGenerationFailedError` (500), `StoryNotFoundError` (404), `SceneNotFoundError` (404)
  - TTS: `TTSAudioNotFoundError` (404), `TTSGenerationFailedError` (500), `EmptySceneItemsError` (400)
  - 보이스: `VoiceNotFoundError` (404), `DefaultVoiceCannotBeModifiedError` (400), `DefaultVoiceCannotBeDeletedError` (400), `InvalidNarratorVoiceError` (400), `InvalidCharacterVoiceError` (400)
  - AI 서버: `AIServerError` (502) — 우리 AI FastAPI 서버 호출 실패(설정/연결/응답). 비동기 Job 안에서 발생하면 `job.error`에 원인이 남는다.
- `app.add_exception_handler(AppException, app_exception_handler)`로 한 곳에서 변환하므로 응답 형태가 일관된다.
- `name`, `appearancePrompt` 필수 + `min_length=1` + 공백만 문자열 금지(`field_validator`)는 Pydantic 단계에서 `422`로 처리된다(FastAPI 기본). PATCH에서도 전달되면 동일 규칙 적용.
- 예상하지 못한 서버 오류는 500으로 처리되며, 별도 전역 핸들러를 추가로 만들지 않는다(FastAPI 기본).

## 비동기 Job / 저장 구조

ComfyUI 실제 생성으로 전환됨에 따라, 작업 시간이 긴 생성은 **비동기 Job**으로 처리한다.

**처리 방식 정책**

| 작업 | 방식 | 비고 |
|---|---|---|
| 캐릭터 이미지 생성 | **비동기** (`run_async`) | ComfyUI 호출. `pending` 즉시 반환 → 폴링 |
| 배경 이미지 생성 | **비동기** (`run_async`) | 우리 AI FastAPI 서버(`AI_SERVER_URL`/generate) 호출 → base64 후보 저장 |
| 보이스 클로닝 | **비동기** (예정) | 무거운 1회성 작업 |
| 최종 영상 렌더링 | **비동기** (예정) | ffmpeg/concat/싱크 |
| 씬 단위 TTS 합성 | **동기** (`run`) | 짧은 합성. 현재 mock은 즉시 `completed`. 길어지면 `run_async`로 전환 가능 |

- **JobManager 2-경로**: `run_async()`(백그라운드, ThreadPoolExecutor) / `run()`(동기, TTS·짧은 작업). [`services/job_manager.py`](app/services/job_manager.py)
- **⚠️ MVP 한계**: in-memory ThreadPoolExecutor라 **서버 재시작 시 pending/running Job 유실**. 단일 프로세스 기준. 배포 시 Redis Queue/Celery/RQ로 교체(이 클래스만 publish 버전으로).
- **프론트 폴링**: `GET /api/jobs/{jobId}`를 `pending/running` 동안 반복 조회(프론트 `utils/pollJob.js` 공통). 캐릭터/배경/클로닝/렌더 공용.
- **orphan 방지**: 캐릭터는 **생성 성공 후 저장**(`reserve_id → generate → create`). 실패 시 레코드 미저장.

**저장(storage) 구조**

- 생성 결과는 DB 없이 **로컬 파일**로 저장하고 `/storage`로 정적 서빙한다.
- 경로는 [`core/config.py`](app/core/config.py)에서 **절대경로**로 관리(`STORAGE_ROOT` + characters/backgrounds/audio/renders). 상대경로 하드코딩 금지(실행 cwd 의존 버그 방지).
- imageUrl 예: `/storage/characters/{characterId}.png` (`storage_url()` 헬퍼).

**저장 책임 경계 (AI ↔ Backend)**

캐릭터·배경 모두 아래 계약으로 동작한다 — **AI는 생성 결과(bytes)만 반환, 저장은 Backend**.

```text
AI(생성)  → 이미지 bytes 반환 (저장 위치는 모름)
            - 캐릭터: in-process ai 모듈(generate_character)이 bytes 반환
            - 배경:   우리 AI FastAPI 서버(/generate)가 base64 반환 → backend가 디코드
Backend  → core/config 경로로 파일 저장 → /storage URL 생성 → repository 저장
```

- 캐릭터: `ai/character_ctrl/character.py`가 storage 직접 저장을 멈추고 bytes를 반환하도록 전환됨(저장은 `character_job_runner`).
- 미구현 씬 이미지 모듈(`face_lock.py`/`pose_expression.py`)도 구현 시 같은 계약을 따른다(직접 저장 금지).

## 구조 리뷰 / 기술부채 기록

보류한 리팩터(분리 트리거 포함)와 팀 결정은 루트 [`BACKEND_TECH_DEBT.md`](../BACKEND_TECH_DEBT.md)에 정리되어 있다.

## ⚠️ 임시 코드 (실제 ComfyUI 연동 시 삭제)

- `GET /api/ai/comfy-health` (`app/routers/ai_health.py`) — 프론트→백엔드→AI→ComfyUI(읽기전용) 연결 확인용 임시 엔드포인트.
- 동작하려면 백엔드에 `COMFYUI_DEFAULT_URL`이 필요해 현재는 `uv run --env-file ai/.env uvicorn ...`로 실행한다.
- 제거 체크리스트: 루트 [`TEMP_AI_CONNECTION_TEST.md`](../TEMP_AI_CONNECTION_TEST.md)

## 추후 구현 예정

- RabbitMQ/Celery 기반 비동기 Job 워커 (`InMemoryJobManager` 교체)
- ComfyUI 실제 연동 및 캐릭터 이미지 생성
- 배경 생성 / 캐릭터 누끼 / 레이어 합성 API
- 보이스 클로닝 / 실제 TTS 합성 (mock API·voiceId 연결은 구현됨, 실제 음성 생성만 남음)
- ffmpeg 영상 렌더링 API
- **Series/Episode 확장** — story를 향후 Series(작품/회차 묶음)의 한 episode로 확장 가능. 현재 전역 라이브러리 구조(캐릭터·배경·보이스 + story.narratorVoiceId / scene.backgroundId / character.voiceId)가 그대로 상위 공유로 이어지므로 지금 구조를 바꿀 필요는 없다. 다회차 제작이 실제로 필요해질 때 착수. 상세 설계 초안: `docs/series_episode_extension_docs_prompt.md`

구현 순서는 `backend/docs/backend_implementation_guide.md` 15절을 참고합니다.

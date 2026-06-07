# 몽실책방 백엔드

FastAPI + PostgreSQL 기반 백엔드 서버입니다. (동화 영상 생성: 스토리 파싱 → 캐릭터/배경 생성 → 보이스/TTS → 씬 편집 → 타임라인 → ffmpeg 렌더)

## 기술 스택

- **FastAPI** (라우터/스키마, Pydantic v2)
- **PostgreSQL** + **SQLAlchemy 2.0** (`Mapped`/`mapped_column`, FK CASCADE/SET NULL, JSONB) + **psycopg3**
- **Alembic** 마이그레이션
- **prefix + ULID** 문자열 ID ([`core/ids.py`](app/core/ids.py))
- 외부 **AI 서버** 호출(이미지/TTS/클로닝) — 백엔드는 ComfyUI/모델을 직접 호출하지 않는다
- 이미지 합성 **Pillow** + **ffmpeg**(imageio-ffmpeg 번들 또는 시스템 ffmpeg) 영상 렌더

## 사전 준비 — PostgreSQL

DB가 있어야 서버가 뜬다(`DATABASE_URL` 필수). 로컬은 docker로 띄운다.

```bash
# 예: pgvector 포함 postgres (docker compose 또는 직접)
docker compose up -d            # aicinematic-pg (port 5432) 등 팀 설정 기준
```

`backend/.env`에 접속 정보를 넣는다(아래 환경변수 표). 그다음 스키마를 올린다:

```bash
cd backend
uv run alembic upgrade head     # 테이블 생성/최신화
```

## 가상환경 / 패키지

프로젝트 루트에서 `uv` 사용(권장, `pyproject.toml` + `uv.lock`이 source of truth).

```bash
uv sync                          # 루트에서
```

`backend/` 안에서 pip로 직접 띄울 경우 `requirements.txt`는 **보조 목록**이다(루트 의존성과 동기화 관리). DB 드라이버(sqlalchemy/psycopg/alembic/ulid 등)는 루트 `pyproject.toml` 기준이므로 uv 사용을 권장한다.

## 서버 실행

```bash
# 루트에서 (env 자동 로드)
uv run --env-file backend/.env uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# backend/ 안에서
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

> `main.py`가 startup 시 `backend/.env` → 없으면 `ai/.env` 순으로 env를 로드한다(`_load_env`). 단 `DATABASE_URL`은 반드시 있어야 한다.

## 주요 URL

| 용도 | 주소 |
|---|---|
| Swagger 문서 | http://127.0.0.1:8000/docs |
| Health check | http://127.0.0.1:8000/api/health |
| 루트 | http://127.0.0.1:8000/ |
| 정적 파일(이미지/오디오/영상) | http://127.0.0.1:8000/storage/... |

## 환경변수

`backend/.env`(gitignore)에 둔다. 실제 주소/시크릿은 코드에 하드코딩하지 않고 `.env`에만 둔다.

| 변수 | 필수 | 용도 |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL 접속 (psycopg3). 없으면 부팅 시 RuntimeError |
| `AI_SERVER_URL` | 이미지 생성 시 | 우리 이미지 AI 서버: `/generate-character`·`/generate-background`·`/generate-pose` |
| `AI_TTS_URL` | TTS 시 | TTS 서버. 백엔드가 `{AI_TTS_URL}/tts` 호출. 미설정이면 audioUrl=null(메타만) |
| `AI_VOICE_CLONE_URL` | 클로닝 시 | 보이스 클로닝 서버 `/clone` (+ 미리듣기 샘플 `/voice-sample`) |
| `QWEN_TTS_ENABLED` | 선택 | `1`이면 `AI_TTS_URL` 없을 때 로컬 Qwen3-TTS 어댑터 사용 |
| `AI_TTS_TIMEOUT_SEC` | 선택 | TTS 요청 timeout(기본 120) |
| `AI_VOICE_CLONE_TIMEOUT_SEC` | 선택 | 클로닝 요청 timeout |
| `FFMPEG_BIN` | 선택 | ffmpeg 경로 직접 지정(없으면 PATH → imageio-ffmpeg 번들 순) |

> env 로드 우선순위: `backend/.env` → 없으면 `ai/.env`(`main.py`의 `_load_env`).

## 폴더 구조

```text
backend/
├── app/
│   ├── routers/                 # FastAPI 라우터(엔드포인트)
│   │   ├── health.py            # /api/health
│   │   ├── stories.py           # 스토리 파싱/조회/삭제 + 나레이터 보이스 + voice-locks
│   │   ├── characters.py        # 캐릭터 CRUD + 생성 Job + 보이스 연결 + 포즈
│   │   ├── jobs.py              # Job 상태 조회
│   │   ├── backgrounds.py       # 배경 프롬프트 추천/생성 Job/라이브러리 CRUD
│   │   ├── scenes.py            # 씬-배경/씬-캐릭터/자막/포즈 연결
│   │   ├── timeline.py          # 타임라인 조회/저장 + render-plan
│   │   ├── tts.py              # 씬/스토리 TTS Job + 조회/삭제
│   │   ├── voices.py            # 보이스 CRUD + 클로닝 + 미리듣기 샘플
│   │   ├── render.py            # 영상 렌더(ffmpeg) 시작/조회
│   │   └── notifications.py     # Job 완료/실패 알림
│   ├── services/                # 비즈니스 로직 (커스텀 예외 발생)
│   │   ├── story_parser.py / story_service.py
│   │   ├── character_service.py / character_job_runner.py / character_pose_job_runner.py
│   │   ├── background_service.py / background_job_runner.py
│   │   ├── voice_service.py / voice_clone_service.py / voice_sample_service.py
│   │   ├── voice_lock_service.py / preset_voice_seed.py
│   │   ├── tts_service.py / tts_job_runner.py
│   │   ├── text_overlay_service.py   # 자막(items에서 파생) cue/layout/색/배경
│   │   ├── timeline_service.py / render_service.py / ffmpeg_render_service.py
│   │   ├── notification_service.py
│   │   ├── job_manager.py / job_service.py   # run_async(ThreadPool)/run(동기)
│   │   ├── ai_character_client.py / ai_background_client.py / ai_pose_client.py
│   │   ├── ai_voice_client.py / tts_ai_client.py   # 외부 AI 서버 호출
│   │   └── image_resolve.py
│   ├── repositories/            # DB 접근 (SQLAlchemy, dict/camelCase 인터페이스 반환)
│   │   ├── story_repo.py / character_repo.py / background_repository.py
│   │   ├── voice_repository.py / tts_audio_repository.py
│   │   ├── job_repo.py / notification_repository.py
│   ├── schemas/                 # Pydantic 요청/응답 모델
│   │   ├── story.py / character.py / background.py / voice.py / tts.py
│   │   ├── text_overlay.py / timeline.py / render.py / job.py / notification.py
│   ├── db/
│   │   ├── base.py              # Declarative Base
│   │   ├── models.py            # 테이블 ORM 모델
│   │   └── session.py           # engine / SessionLocal (DATABASE_URL)
│   ├── core/
│   │   ├── config.py            # storage 경로(절대경로) + AI 서버 URL + ffmpeg 탐색
│   │   ├── ids.py               # prefix + ULID ID 생성/검증
│   │   ├── exceptions.py        # AppException + 도메인별 커스텀 예외
│   │   └── exception_handlers.py # AppException → HTTP 응답 변환
│   ├── storage/                 # 생성 결과물(이미지/오디오/영상) — git 제외, /storage 서빙
│   └── main.py                  # 앱 생성/라우터 등록/startup/정적 서빙
├── alembic/                     # 마이그레이션
│   ├── versions/
│   └── env.py
├── alembic.ini
├── docs/                        # 백엔드 작업 명세/가이드
├── requirements.txt             # pip 보조 목록(루트 uv가 정본)
└── README.md
```

## 영속성 (PostgreSQL)

- 모든 도메인은 **PostgreSQL**에 저장된다(과거 in-memory mock에서 전환 완료).
- **PK = `{prefix}{ULID}`** ([`core/ids.py`](app/core/ids.py)): `story_…`, `scene_…`, `char_…`, `bg_…`, `voice_…`, `audio_…`, `render_…`, `job_…`, `notif_…` 등. 숫자 PK 미사용, ULID라 시간순 정렬.
  - 단, **API 계약상 `sceneId`는 `scene_{order:03d}`**(예: `scene_001`) — order_index로 해석해 내려준다(내부 PK와 별개).
  - preset 보이스 같은 **시스템 고정 ID**는 ULID 규칙 밖에서 직접 지정(`voice_preset_narrator_calm_001` 등).
- **마이그레이션**: `uv run alembic upgrade head`. 새 컬럼 추가 시 `alembic/versions/`에 리비전 추가.
- repository는 SQLAlchemy 세션으로 접근하지만 **상위 레이어엔 dict/camelCase**로 반환(서비스/라우터는 ORM 객체에 직접 의존하지 않음).

### storage 레이아웃 ([`core/config.py`](app/core/config.py))

생성 결과물은 DB가 아니라 로컬 파일로 저장하고 `/storage`로 정적 서빙한다(경로는 절대경로 관리, cwd 의존 버그 방지).

```text
storage/
├── characters/{characterId}.png
├── character_poses/...
├── backgrounds/library/{backgroundId}.png   # 저장본(영구)
├── voices/{voiceId}/                         # 보이스 자산(reference + sample.wav)
├── audio/{audioId}.wav                       # TTS 결과
└── renders/{renderId}.mp4                    # 영상 렌더 결과
```

## startup 동작 ([`main.py`](app/main.py))

- **preset 나레이션 4종 seed** — `seed_preset_narrator_voices()`가 매 부팅 idempotent upsert. DB 초기화/팀원 환경에서도 항상 기본 나레이션 선택 가능. 동봉 샘플이 `app/seed_assets/preset_voices/{voiceId}.wav`에 있으면 storage로 복사해 미리듣기 활성화.
- **미완료 TTS 재개** — `resume_unfinished_story_tts_jobs()`로 재시작 시 중단된 스토리 TTS Job 복구.
- `/storage` 정적 마운트.

## 구현된 API

### 시스템 / 스토리
| Method | Endpoint | 설명 |
|---|---|---|
| GET | `/` | 서비스 상태 |
| GET | `/api/health` | 헬스 체크 |
| POST | `/api/stories/parse` | 대본 파싱(raw/structured) 후 저장 |
| GET | `/api/stories` | 스토리 목록 |
| GET | `/api/stories/emotions` | 감정 셀렉터 옵션 `[{label,value}]` |
| GET | `/api/stories/{story_id}` | 스토리 단건(씬 포함) |
| DELETE | `/api/stories/{story_id}` | **스토리 삭제** (씬/씬-캐릭터/TTS/렌더는 FK CASCADE + 파일 정리; 캐릭터·배경은 공용이라 유지) |
| PATCH | `/api/stories/{story_id}/narrator-voice` | 나레이션 보이스 연결/해제 |
| GET | `/api/stories/{story_id}/voice-locks` | 대상별(나레이션/캐릭터) 잠금 상태 + 다음 단계 가능 여부 |
| POST | `/api/stories/{story_id}/voice-locks/{targetType}/{targetId}/lock` | 대상 잠금 + 해당 TTS 생성 시작 |
| POST | `/api/stories/{story_id}/voice-locks/{targetType}/{targetId}/unlock` | 대상 잠금 해제(ttsStatus=stale) |

### 캐릭터 / Job
| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/api/characters/generate` | 캐릭터 생성 Job(비동기 → pending, 폴링) |
| GET | `/api/characters` | 목록 |
| POST | `/api/characters` | 결과 직접 저장 |
| GET | `/api/characters/{id}` | 단건 |
| PATCH | `/api/characters/{id}` | 부분 수정(name/appearancePrompt/imageUrl) |
| DELETE | `/api/characters/{id}` | 삭제 |
| PATCH | `/api/characters/{id}/voice` | 보이스 연결/해제(body: voiceId) |
| POST | `/api/characters/{id}/poses/generate` | 포즈 생성 Job(body: posePrompt; aiImagePath 없으면 400) |
| GET | `/api/characters/{id}/poses` | 포즈 목록(1:N) |
| GET | `/api/jobs/{job_id}` | Job 상태 조회 |

### 배경 / 씬
| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/api/backgrounds/prompt-suggestions` | 씬 기반 프롬프트 추천(이미지 X) |
| POST | `/api/backgrounds/generate` | 배경 생성 Job(비동기; body `{name, prompt}`) → 생성·라이브러리 자동 저장 |
| GET | `/api/backgrounds` | 목록 |
| GET | `/api/backgrounds/{id}` | 단건 |
| PATCH | `/api/backgrounds/{id}` | 수정(name) |
| DELETE | `/api/backgrounds/{id}` | 삭제(+참조 씬 backgroundId null) |
| PATCH | `/api/scenes/{scene_id}/background` | 씬-배경 연결(body: storyId, backgroundId) |
| PATCH | `/api/scenes/{scene_id}/character` | 씬에 캐릭터 추가/수정(씬당 다중) |
| DELETE | `/api/scenes/{scene_id}/character/{character_id}` | 씬에서 캐릭터 1명 제거 |
| PATCH | `/api/scenes/{scene_id}/subtitles` | 자막 설정 저장(items 자동 생성; cueOrder/layout + 씬 글자색/배경) |
| PATCH | `/api/scenes/{scene_id}/characters/{character_id}/pose` | 씬 캐릭터 포즈 적용/해제 |

### 보이스 / TTS
| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/api/voices` | 보이스 자산 생성(name 필수) |
| GET | `/api/voices` | 목록(사용자 + preset) |
| GET | `/api/voices/{id}` | 단건 |
| PATCH | `/api/voices/{id}` | 수정(name/description/voicePrompt) |
| DELETE | `/api/voices/{id}` | 삭제(+참조 캐릭터 voiceId·스토리 narratorVoiceId null) |
| POST | `/api/voices/clone` | **보이스 클로닝**(업로드 음성 → 비동기 Job) |
| POST | `/api/voices/{id}/sample` | 미리듣기 샘플 생성 |
| POST | `/api/voices/presets/samples` | preset 나레이션 4종 샘플 일괄 생성 |
| POST | `/api/tts/scene` | 씬 TTS Job |
| POST | `/api/tts/story` | 스토리 전체 TTS Job |
| GET | `/api/tts?storyId=&sceneId=` | 씬별 TTS 결과 |
| DELETE | `/api/tts/{audio_id}` | TTS 결과 삭제 |

### 타임라인 / 렌더 / 알림
| Method | Endpoint | 설명 |
|---|---|---|
| GET | `/api/stories/{story_id}/timeline` | 타임라인 조회(order/ duration/totalDuration/readyStatus/cueTimings) |
| PATCH | `/api/stories/{story_id}/timeline` | 타임라인 저장(전체 scene; duration + cue 타이밍) |
| GET | `/api/stories/{story_id}/render-plan` | 렌더 플랜(배경/캐릭터 layout/자막 데이터) |
| GET | `/api/stories/{story_id}/render` | 최신 렌더 결과 조회 |
| POST | `/api/stories/{story_id}/render` | **영상 렌더링(ffmpeg)** 시작 → 음성 포함 mp4 |
| GET | `/api/notifications?limit=` | 알림 목록(created_at desc) |
| GET | `/api/notifications/unread-count` | 안 읽은 개수 `{count}` |
| PATCH | `/api/notifications/{id}/read` | 단일 읽음 |
| PATCH | `/api/notifications/read-all` | 전체 읽음 `{updated}` |
| DELETE | `/api/notifications/{id}` | 단일 삭제(204 / 404) |
| DELETE | `/api/notifications` | 전체 삭제 `{deleted}` |

> 알림은 `job_manager`가 job 완료/실패 직후 자동 생성(character/background/voice_clone/tts/tts_story/render). 같은 job 중복은 `UNIQUE(related_job_id, type)`로 차단. 저장은 `notifications` 테이블.

## 스토리 파싱 규칙

- 빈 줄 기준 씬 분리. `화자: "대사"`(큰따옴표) → `dialogue`, 그 외 → `narration`.
- `inputMode`: `raw`(textarea 본문) / `structured`(씬·item 구조화) 둘 다 지원.
- 나레이션 화자명 정규화: `나레이션`/`내레이션`/`narration`은 화자 없는 narration으로 처리.

### 감정 태그
각 줄 맨 앞에 선택적 `[감정]`. 결과 item에 `emotion`(영문) + `emotionLabel`(한글)이 **항상** 포함.

- 지원: 기본(neutral)·잔잔함(calm)·기쁨(happy)·슬픔(sad)·화남(angry)·무서움(scared)·신남(excited)·다정함(friendly)·진지함(serious)
- 우선순위: ① 유효한 `[감정]` 태그 → ② 없으면 본문 키워드 추정 → ③ 타입 기본값(narration=calm, dialogue=neutral)
- 태그가 있으면(유효/무효 무관) 키워드 추정 안 함. 키워드는 부분 매칭이라 **명확한 표현만** 사용.

## 보이스 / TTS / 클로닝

보이스는 **storyId 없는 전역 라이브러리 자산**이다. 보이스를 만들어 `voiceId`를 발급하고, 캐릭터(`character.voiceId`)와 스토리 나레이션(`story.narratorVoiceId`)이 그 voiceId를 참조한다.

- **역할 분리**: 백엔드는 자산 정체성·참조만 관리. 실제 합성/클로닝은 AI/TTS 파트.
- **연결 제한 기준 = `status=ready`** (voiceType은 추천 태그일 뿐 제한 안 함).
- **삭제 캐스케이드**: 보이스 삭제 시 참조 캐릭터 voiceId / 스토리 narratorVoiceId를 null.
- **클로닝**(`POST /api/voices/clone`): 업로드 음성을 `{AI_VOICE_CLONE_URL}/clone`에 보내 복제, `referenceAudioUrl` 저장. 비동기 Job.
- **미리듣기 샘플**: `{AI_TTS_URL}/voice-sample`(없으면 `/tts` fallback)로 생성 → `storage/voices/{voiceId}/sample.wav` 저장 → `sampleAudioUrl` 갱신.

### 기본 나레이션 preset 4종

부팅 시 idempotent seed. `GET /api/voices`에 `voiceType="narrator" && isPreset=true`로 노출. **preset은 수정·삭제 불가(400).**

| voiceId | 이름 |
|---|---|
| `voice_preset_narrator_calm_001` | 차분한 나레이션 |
| `voice_preset_narrator_bright_001` | 밝은 나레이션 |
| `voice_preset_narrator_soft_001` | 부드러운 나레이션 |
| `voice_preset_narrator_serious_001` | 진지한 나레이션 |

> ⚠️ **실제 화자(Qwen 음성)는 AI 서버의 `voiceId → 화자` 매핑이 결정**한다(백엔드는 voiceId만 전달, payload의 `speaker` 필드는 캐릭터 매칭용이라 화자 선택과 무관). 화자를 바꾸려면 AI 서버 매핑을 변경해야 한다.

### TTS 동작
- **scene/story 단위** 생성. `scene.items`(text/emotion/speaker)를 사용, 백엔드가 `audioId` 발급 후 AI/TTS에 전달.
- 호출: `AI_TTS_URL` 우선 → 없으면 `QWEN_TTS_ENABLED=1`일 때 로컬 Qwen3-TTS → 둘 다 없으면 `audioUrl=null`(메타만).
- 감정은 그대로 통과(`item.emotion`/`emotionLabel`). 목소리=voiceId(캐릭터/나레이터 고정), 감정=문장별.
- **재생성 = 교체**(같은 storyId+sceneId 재생성 시 기존 audio 삭제 후 교체).
- **클론 voiceId**: 합성 시 `referenceAudioUrl` → **`referenceAudioBase64`로 변환해 전송**(AI 서버가 다른 PC라 /storage URL을 못 읽으므로 바이트 동봉).
- `audioDurationSec`는 백엔드가 wav 파일에서 실측(AI가 durationSec 미반환 대비).

## 자막 (Text Overlay)

자막은 별도 저장 없이 **`scene.items`에서 줄당 1개 자동 파생**한다(텍스트 읽기전용). 저장하는 건 줄별 `cueOrder`(그룹) + `layout`(정규화 위치/크기/정렬) + **씬 단위 글자색/배경**.

- `PATCH /api/scenes/{scene_id}/subtitles` body: `{storyId, sceneTextColor?, subtitleBackground?('none'|'black'|'white'), overlays:[{itemIndex, cueOrder, layout}]}`
- 단일 소스 `build_text_overlays()`가 `overlay.style`을 조립 → **씬편집·타임라인·ffmpeg 렌더가 모두 같은 style을 읽어** 위치/색/배경이 일치.
- **자막 배경 박스**(씬 단위): `none`(투명) / `black`(rgba 0,0,0,0.3) / `white`(rgba 255,255,255,0.3), 둥근 박스. 불투명도 0.3 고정(상수).

## 타임라인 / 렌더

- 타임라인은 **story 단위**로 scene 재생 길이(`duration`)와 **cue 그룹 타이밍**(`cueOrder`별 startSec/durationSec)만 관리. **순서는 스토리 원본 고정**(재정렬 X), duration 1.0~30.0.
- `readyStatus`: hasBackground/hasCharacters/hasText + hasAudio(모든 줄 ready) + audioStatus.
- **렌더**(`POST /api/stories/{story_id}/render`): Pillow 프레임 합성(배경→캐릭터→자막) → ffmpeg 단일 패스 인코딩. 타임라인 cue.items의 TTS 음성을 adelay+amix로 mux → **음성 포함 mp4**(`storage/renders/{renderId}.mp4`).
  - 렌더 전 검증: 모든 필수 보이스 locked + 실패 없음 + cue audioUrl 존재 → 아니면 400.

## 비동기 Job 구조

| 작업 | 방식 |
|---|---|
| 캐릭터 이미지 생성 | 비동기 (`run_async`, AI_SERVER_URL `/generate-character`) |
| 배경 이미지 생성 | 비동기 (`run_async`, AI_SERVER_URL `/generate-background`) |
| 캐릭터 포즈 생성 | 비동기 (`/generate-pose`) |
| 보이스 클로닝 | 비동기 (AI_VOICE_CLONE_URL `/clone`) |
| 영상 렌더링 | 비동기 (ffmpeg) |
| TTS 합성 | 비동기 Job (scene/story) |

- **JobManager 2-경로**: `run_async()`(ThreadPoolExecutor) / `run()`(동기). [`services/job_manager.py`](app/services/job_manager.py)
- ⚠️ **MVP 한계**: in-memory ThreadPool이라 서버 재시작 시 pending/running Job 유실(단, TTS는 startup에서 재개 시도). 배포 시 Redis Queue/Celery로 교체.
- **프론트 폴링**: `GET /api/jobs/{jobId}`(`utils/pollJob.js` 공통).
- **orphan 방지**: 생성 성공 후 저장(실패 시 레코드 미저장).

## AI 서버 호출 계약 (Backend ↔ AI)

백엔드는 외부 AI 서버만 호출하고 ComfyUI/모델은 직접 호출하지 않는다.

```text
이미지: Backend → AI_SERVER_URL /generate-character|/generate-background|/generate-pose → base64(들) 반환 → Backend가 storage 저장
TTS  : Backend → AI_TTS_URL /tts (+ referenceAudioBase64) → audioUrl/base64 반환 → Backend가 /storage/audio 저장
클론  : Backend → AI_VOICE_CLONE_URL /clone (업로드 음성) → reference 저장
```

- Backend는 프롬프트/레퍼런스만 보내고 seed/steps/model 등은 보내지 않는다(AI 서버/워크플로 내부 책임).
- 연결/응답 실패 시 mock fallback 없이 Job `failed`(원인을 `error`에 보존). AI 서버 오류는 `AIServerError`(502).

## 예외 처리 (계층 분리)

```text
repository  → 결과만 반환(없으면 None). HTTPException 의존 X
service     → 비즈니스 예외 판단(커스텀 예외 raise)
router      → request 수신 → service 호출 → 응답
global      → main.py 등록 app_exception_handler가 AppException → {"detail": ...}
```

주요 커스텀 예외(`core/exceptions.py`, 모두 `AppException` 상속):
- 404: `StoryNotFoundError`, `SceneNotFoundError`, `CharacterNotFoundError`, `BackgroundNotFoundError`, `VoiceNotFoundError`, `JobNotFoundError`, `TTSAudioNotFoundError`, `CharacterPoseNotFoundError`, `NotificationNotFoundError`, `VoiceLockTargetNotFoundError`
- 400: `NoFieldsToUpdateError`, `EmptySceneItemsError`, `TimelineValidationError`, `CueTimingValidationError`, `VoiceNotReady/NotConnectedError`, `Invalid(Narrator|Character)VoiceError`, `DefaultVoiceCannotBe(Modified|Deleted)Error`, `CharacterPoseSourceMissingError`, `RenderPlanInvalidError`, `RenderAudioNotReadyError`
- 500/502: `*GenerationFailedError`(500), `AIServerError`/`PoseGenerationFailedError`(502), `FFmpeg*Error`
- Pydantic 검증 실패(필수/공백 등)는 FastAPI 기본 `422`.

## 문서

- 작업 명세/가이드: [`backend/docs/`](docs/) (DB/PostgreSQL, TTS, 클로닝, 타임라인, 자막, 포즈, 나레이터 preset 등)
- 백엔드 ↔ AI/TTS JSON 계약: 루트 `TTS_AI_CONTRACT.md`
- 보류 리팩터/기술부채: 루트 `BACKEND_TECH_DEBT.md`

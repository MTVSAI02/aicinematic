# 프론트 기준 스토리 생성 플로우 테스트 가이드

캐릭터/배경이 실제 AI FastAPI 서버와 연결된 뒤, 프론트에서 스토리 입력 → 씬 → 캐릭터/배경 생성 → 씬 연결까지
한 번에 점검하기 위한 **수동 테스트 가이드**다. (코드 수정 없이 화면에서 직접 진행)

> 코드와 대조해 검증된 가이드다. 요청 초안 대비 보정된 5가지는 본문에 ⚠️ 로 표시했다.

---

## 0. 전제조건 (시작 전 반드시 확인)

| 항목 | 확인 방법 / 값 |
|---|---|
| AI 서버 가동 | 브라우저에서 `http://192.168.0.35:5000/docs` 열림 (200). `/generate-character`, `/generate-background` 보이면 OK |
| 같은 네트워크 | `192.168.0.35`는 사내 LAN. Wi-Fi/VPN으로 같은 망에 붙어 있어야 함 (`ping 192.168.0.35` 응답 확인) |
| backend `.env` | `AI_SERVER_URL=http://192.168.0.35:5000` 가 `backend/.env`에 있어야 함 (없으면 실제 AI 연결 안 됨) |
| 백엔드 실행 | 루트에서 `uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000` |
| 프론트 실행 | `cd frontend && npm run dev` → `http://localhost:5173` |
| API base | 프론트는 `VITE_API_BASE_URL=http://localhost:8000` 을 호출 (백엔드 포트는 **8000** 고정) |

> ⚠️ **저장소는 in-memory mock**이다. 백엔드를 **재시작하면** 스토리/캐릭터/배경/씬 연결 레코드가 모두 사라진다
> (이미지 파일은 `backend/app/storage/`에 남지만 고아 상태가 됨). 테스트 1회는 **백엔드를 켜둔 채** 끝까지 진행할 것.

---

## 1. 테스트 시작 URL & 순서

시작: `http://localhost:5173/story-input`

```text
① /story-input    스토리 입력 → "씬 분해하기"
② /scene-check    씬/대사/나레이션/감정 확인 (읽기 전용)
③ /character      어린왕자·여우 생성
④ /background     어린왕자의 별·사막 배경 생성 → 후보 선택 → 라이브러리 저장
⑤ /scene-editor   씬에 배경/캐릭터 연결   ⚠️ (연결은 scene-check가 아니라 여기서)
⑥ 새로고침 후 유지 확인 (③④⑤ 페이지)
```

페이지 이동은 각 페이지 하단 이동 버튼 또는 상단 NavBar, 혹은 위 URL 직접 입력으로 한다.

---

## 2. 페이지별 테스트

### ① 스토리 입력 — `/story-input`
- **입력**: `제목`(⚠️ **필수**, 예: `어린 왕자`) + 본문 textarea(아래 §3 스토리 붙여넣기)
- **버튼**: `씬 분해하기` (제목·본문 둘 다 있어야 활성화)
- **정상**: 분해 성공 시 자동으로 `/scene-check` 로 이동
- **실패 위치**: 입력 폼 하단 빨간 문구 `"스토리 분석에 실패했습니다. 백엔드 서버가 실행 중인지 확인..."`
- **API**: `POST /api/stories/parse`

### ② 씬 확인 — `/scene-check` (읽기 전용)
- **버튼 없음**. 분해된 씬 목록이 보임. (연결 기능 없음 — 연결은 ⑤에서)
- **정상**: 씬별로 `씬 N`, 각 줄의 화자/내레이션 구분, `🎭 감정라벨` 표시
- **새로고침 OK**: URL이 `/scene-check?storyId=story_mock_001` 형태라, 새로고침해도 그 storyId로 백엔드(`GET /api/stories/{id}`)에서 씬을 다시 불러온다. (단 URL의 `?storyId=`가 없는 채로 새로고침하면 비어짐 → ①부터)

### ③ 캐릭터 생성 — `/character`
- **입력(새 캐릭터 생성 폼)**: `이름`, `외형 설명`(= description), `외형 프롬프트`(= appearancePrompt)
- **버튼**: `캐릭터 생성` (이름·외형 프롬프트 필수)
- **정상**: 버튼이 `생성 중...` → 상태문구 `생성 대기 중 → 생성 중 → 완료` → 아래 **캐릭터 라이브러리**에 이미지 카드 표시
- **실패 위치**: 폼 하단 빨간 에러 문구 (Job 실패 시 실제 원인 표시)
- **API**: `POST /api/characters/generate` → `GET /api/jobs/{jobId}` 폴링(자동)

### ④ 배경 생성 — `/background`
- **입력**: `배경 프롬프트` textarea (씬 추천은 선택)
- **버튼 순서**:
  1. `배경 후보 생성` → ⚠️ **후보 4장** 그리드 표시
  2. 후보 1장 선택 → `3. 선택한 후보 저장`에서 **이름 입력 후 저장** → 라이브러리에 추가
- **정상**: 후보 4장 표시 → 저장 시 "4. 배경 라이브러리"에 등장 (⑤에서 연결하려면 **저장 필수**)
- **실패 위치**: 패널 하단 빨간 에러 문구
- **API**: `POST /api/backgrounds/generate` → `GET /api/jobs/{jobId}` 폴링 → 저장은 `POST /api/backgrounds`

### ⑤ 씬 편집(연결) — `/scene-editor`
- **선택**: 상단 `스토리` 드롭다운에서 방금 만든 스토리 → 좌측 사이드바에서 `씬 N` 클릭
- **배경 연결**: 우측 `배경` 패널 → 라이브러리에서 배경 선택 → `이 씬에 배경 연결`
- **캐릭터 연결(다중)**: `캐릭터` 패널 → 캐릭터 선택 → (선택) 연출 prompt 입력 → `이 씬에 캐릭터 추가` (여러 명 반복 가능, `제거`로 해제)
- **정상**: `배경이 씬에 연결되었습니다` / `캐릭터가 씬에 추가되었습니다` 메시지 + 사이드바 씬에 `배경: ...`, `캐릭터 N명` 배지
- **실패 위치**: 편집 영역 하단 빨간 에러 문구
- **API**: `PATCH /api/scenes/{sceneId}/background`, `PATCH /api/scenes/{sceneId}/character`

---

## 3. 테스트용 스토리 (제목 + 본문)

- **제목**: `어린 왕자`
- **본문**:

```text
[잔잔함] 어린왕자는 작은 별 위에 앉아 노을을 바라보고 있었다.
하늘은 금빛과 보라빛으로 천천히 물들고 있었다.

[다정함] 어린왕자: "안녕, 너는 어디에서 왔니?"

작은 여우는 모래 언덕 뒤에서 조심스럽게 걸어 나왔다.
바람은 사막의 고운 모래를 부드럽게 흔들었다.

[기쁨] 여우: "나는 친구를 찾고 있었어."

어린왕자는 미소를 지으며 여우에게 손을 내밀었다.
두 친구는 별빛이 떠오르는 사막을 함께 걸어갔다.
```

확인 포인트: 빈 줄 기준 씬 분리 / `화자: "대사"`는 dialogue·나머지 narration / `[잔잔함]`(calm)·`[다정함]`(friendly)·`[기쁨]`(happy) 감정 반영.

---

## 4. 캐릭터 생성 입력값

**어린왕자**
```json
{
  "name": "어린왕자",
  "description": "작은 별에서 온 호기심 많고 다정한 소년 캐릭터",
  "appearancePrompt": "A young little prince with short golden blond hair, a green coat, a small scarf, gentle eyes, cute storybook character, full body, soft pastel illustration style"
}
```
**여우**
```json
{
  "name": "여우",
  "description": "어린왕자와 친구가 되는 따뜻하고 조심스러운 작은 여우",
  "appearancePrompt": "A small cute orange fox with soft fluffy fur, gentle eyes, warm expression, storybook animal character, full body, soft pastel illustration style"
}
```
확인: ① 요청 전송 ② Job 생성 ③ polling completed ④ `images[0]` base64 decode ⑤ `storage/characters/` 저장 ⑥ imageUrl 표시 ⑦ 새로고침 유지(백엔드 켜둔 채) ⑧ **description은 생성 prompt에 안 섞이고 메타로만 저장**.

> 참고: 해상도/seed/steps 등은 AI 서버 워크플로가 정함(backend는 `{prompt}`만 전송). 결과 해상도는 서버 워크플로에 따름.

---

## 5. 배경 생성 prompt

**어린왕자의 별**
```text
A tiny peaceful asteroid planet at sunset, golden and purple sky, soft glowing stars, dreamy storybook background, watercolor pastel style, clean composition, background only, no characters
```
**사막과 노을**
```text
A wide quiet desert at sunset, soft sand dunes, warm golden light, purple evening sky, small stars beginning to appear, magical storybook background, clean composition, background only, no characters
```
확인: ① 요청 전송 ② backend가 `AI_SERVER_URL/generate-background` 호출 ③ images 배열 처리 ④ **후보 4장 표시** ⑤ 선택→라이브러리 저장 ⑥ scene.backgroundId 연결 ⑦ 새로고침 유지 ⑧ 캐릭터/사람/동물/글자/워터마크 없음(육안).

---

## 6. 씬 연결 (scene-editor에서)

**Scene 1** = `scene_001`
```json
{
  "sceneId": "scene_001",
  "backgroundId": "<어린왕자의 별 배경 ID>",
  "characters": [
    { "characterId": "<어린왕자 ID>", "sceneAppearancePrompt": "작은 별 위에 앉아 노을을 바라보는 모습" }
  ]
}
```
**Scene 2** = `scene_002`
```json
{
  "sceneId": "scene_002",
  "backgroundId": "<사막과 노을 배경 ID>",
  "characters": [
    { "characterId": "<어린왕자 ID>", "sceneAppearancePrompt": "사막에서 여우에게 다정하게 손을 내미는 모습" },
    { "characterId": "<여우 ID>", "sceneAppearancePrompt": "모래 언덕 뒤에서 조심스럽게 걸어 나오는 모습" }
  ]
}
```
확인: ① 씬당 캐릭터 다중 ② characterId 저장 ③ 캐릭터별 sceneAppearancePrompt 저장 ④ backgroundId 저장 ⑤ 새로고침 유지(scene-editor 재진입 시 배지 유지).

> ⚠️ 실제 씬 개수/순서는 §3 본문 분해 결과에 따른다. 빈 줄 블록 단위로 `scene_001`부터 매겨지므로, 위 scene_001/002가 어느 문단인지 ② 화면에서 먼저 확인할 것.

---

## 7. Network 탭 확인 (개발자도구)

| 요청 | request body | response (정상) | status |
|---|---|---|---|
| `POST /api/stories/parse` | `{ "title": "어린 왕자", "script": "<본문>" }` ⚠️(title 포함) | `{ storyId, title, scenes:[...] }` | 200 |
| `POST /api/characters/generate` | `{ name, description, appearancePrompt }` | `{ jobId, status:"pending", message }` | 200 |
| `GET /api/jobs/{jobId}` | — | `{ jobId, type, status, progress, result, error }` (완료 시 status=`completed`) | 200 |
| `POST /api/backgrounds/generate` | `{ "prompt": "<배경 prompt>" }` | `{ jobId, status:"pending", message }` | 200 |
| `GET /api/jobs/{jobId}` | — | `result.candidates` 4개 | 200 |
| `PATCH /api/scenes/{sceneId}/character` | `{ storyId, characterId, sceneAppearancePrompt }` | `{ storyId, sceneId, characters:[...] }` | 200 |
| `PATCH /api/scenes/{sceneId}/background` | `{ storyId, backgroundId }` | `{ storyId, sceneId, backgroundId }` | 200 |

실패 시: response body의 `detail`(4xx/5xx) 또는 Job의 `error` 필드에 실제 원인이 담긴다.

---

## 8. AI 서버 API 계약 (참고)

```text
POST {AI_SERVER_URL}/generate-character   req: { "prompt": "<characterFinalPrompt>" }   res: { "images": ["<base64>"] }            (1장, images[0] 사용)
POST {AI_SERVER_URL}/generate-background  req: { "prompt": "<backgroundFinalPrompt>" }  res: { "images": ["<base64>", x4] }        (4장)
```
backend는 seed/steps/cfg/model/width/height/negative_prompt 를 **보내지 않음** (AI 서버/ComfyUI 워크플로 책임).

---

## 9. 실패 시 로그 위치

| 위치 | 무엇을 보나 |
|---|---|
| 브라우저 Network 탭 | 요청 status, response `detail`/`error` |
| 브라우저 화면 | 각 폼/패널 하단 빨간 에러 문구 |
| 백엔드 터미널 | uvicorn 콘솔 (예외 트레이스백) |
| Job 결과 | `GET /api/jobs/{jobId}` 의 `error` (AI 서버 연결/응답 실패 원인 그대로 노출, mock fallback 없음) |
| AI 서버 | 연결 자체 실패면 `AIServerError`(502 계열) 메시지 — AI 서버 가동/네트워크부터 확인 |

---

## 10. 테스트 결과 기록표

| 구분 | 테스트 항목 | 기대 결과 | 실제 결과 | 통과 | 비고 |
|---|---|---|---|---|---|
| 스토리 | 스토리 파싱 | 씬/대사/나레이션 분리 + 감정 반영 | | | |
| 캐릭터 | 어린왕자 생성 요청 | Job 생성(pending) | | | |
| 캐릭터 | 어린왕자 이미지 표시 | 라이브러리에 이미지 | | | |
| 캐릭터 | 여우 생성 요청 | Job 생성(pending) | | | |
| 캐릭터 | 여우 이미지 표시 | 라이브러리에 이미지 | | | |
| 배경 | 어린왕자의 별 배경 | 후보 4장 표시 | | | |
| 배경 | 사막과 노을 배경 | 후보 4장 표시 | | | |
| 배경 | 후보 → 라이브러리 저장 | 라이브러리에 등장 | | | |
| 씬 연결 | Scene 1 캐릭터 연결 | 어린왕자 연결(배지) | | | |
| 씬 연결 | Scene 1 배경 연결 | 어린왕자의 별 연결 | | | |
| 씬 연결 | Scene 2 캐릭터 2명 | 어린왕자+여우 연결 | | | |
| 씬 연결 | Scene 2 배경 연결 | 사막 배경 연결 | | | |
| 유지 | 브라우저 새로고침(백엔드 ON) | imageUrl·씬 연결·씬 목록 유지 | | | scene-check는 URL `?storyId=` 있을 때 유지 |

---

## 11. 빠른 체크리스트 (요약)

1. AI 서버 `/docs` 열림 + `AI_SERVER_URL` env 설정 + `ping 192.168.0.35` 응답
2. 백엔드 `:8000`, 프론트 `:5173` 둘 다 실행
3. `/story-input`에 **제목+본문** 입력 → 씬 분해
4. `/character`에서 어린왕자·여우 생성(이미지 뜰 때까지 대기)
5. `/background`에서 배경 2종 생성 → 후보 4장 중 1장씩 **라이브러리 저장**
6. `/scene-editor`에서 스토리·씬 선택 → 배경/캐릭터 연결
7. Network 탭으로 §7 요청 status/body 확인
8. 브라우저 새로고침으로 유지 확인 (백엔드는 끄지 말 것)

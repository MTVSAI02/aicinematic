# 몽실책방 프론트엔드

> 사용자가 입력한 동화 대본을 장면으로 분해하고, 캐릭터·배경·음성·자막을 조립해 짧은 “움직이는 동화책 영상”을 만드는 React 프론트엔드입니다.

이 문서는 `frontend/` 작업자가 몽실책방의 도메인, 화면 흐름, 상태 관리, API 연동 규칙, TTS/보이스 클로닝 흐름, 디자인 규칙을 이해하고 일관되게 개발하기 위한 기준 문서입니다.

---

## 1. 서비스 방향

서비스명은 **몽실책방**입니다.

몽실책방은 사용자가 입력한 동화 이야기를 바탕으로 다음 흐름을 제공합니다.

```text
스토리 입력
→ 씬 분해
→ 캐릭터 생성 또는 불러오기
→ 캐릭터 목소리 선택 또는 보이스 클로닝
→ 배경 생성
→ 캐릭터와 배경 합성
→ 씬별 TTS 음성 생성
→ 자막·타임라인 확인
→ 짧은 동화 영상 출력
```

몽실책방의 핵심은 AI가 영상을 완전히 자동 생성하는 것이 아니라,  
AI가 만든 캐릭터·배경·음성 에셋을 사용자가 조립해 **움직이는 동화책**을 완성하는 것입니다.

프론트엔드는 AI 모델을 직접 실행하지 않습니다.

프론트의 역할은 다음과 같습니다.

```text
1. 사용자 입력을 받는다.
2. 백엔드 API를 호출한다.
3. 백엔드가 반환한 story, scene, character, voice, render 상태를 저장한다.
4. 각 단계 화면에서 사용자가 확인·수정할 수 있게 보여준다.
5. 캐릭터의 외형과 목소리가 함께 재사용될 수 있도록 characterId와 voiceId 연결 상태를 관리한다.
```

---

## 2. 현재 개발 범위

현재 프론트에서 고려해야 하는 개발 범위는 다음과 같습니다.

| 영역 | 상태 | 프론트 역할 |
| --- | --- | --- |
| Health Check | 연동 대상 | 백엔드 연결 상태 확인 |
| Story Parse | 연동 대상 | 대본 입력 후 `POST /api/stories/parse` 호출 |
| Scene Check | 연동 대상 | 백엔드 응답의 `sceneId`, `items` 기준으로 씬 카드 표시 |
| Character Library | ✅ 연동됨 | 캐릭터 생성(Job)·목록 조회·수정·삭제·선택을 백엔드 API와 연동 완료 |
| Background Library | ✅ 연동됨 | 배경 프롬프트 추천·후보 생성(Job)·선택 저장·수정·삭제·씬 연결을 백엔드 API와 연동 완료 (`/background`) |
| Voice Mapping | ✅ 연동됨 | 나레이션(`story.narratorVoiceId`)·캐릭터(`character.voiceId`)에 보이스 연결, 보이스 라이브러리 CRUD를 백엔드 API와 연동 완료 (`/voice`) |
| Voice / TTS 합성 | 개발 대상 | 씬 item 기준 음성 생성 요청 및 결과(audioUrl) 재생 — AI 연동 이후 단계 |
| Scene Editor | 개발 대상 | 배경·캐릭터 합성 결과 표시 준비 |
| Timeline | 개발 대상 | 씬 순서, 길이, 음성 길이 반영 |
| Export | 개발 대상 | 렌더링 진행률과 결과 다운로드 표시 |

### 중요한 범위 정리

```text
TTS = MVP 필수 기능
보이스 클로닝 = 현재 개발 범위에 포함된 캐릭터 재사용 강화 기능
```

보이스 클로닝은 단독 기능이 아니라,  
**캐릭터 라이브러리에서 외형과 목소리를 함께 저장하고 재사용하기 위한 기능**입니다.

따라서 프론트는 캐릭터를 관리할 때 이미지 정보만 보지 말고,  
해당 캐릭터에 연결된 `voiceId` 또는 `voiceProfile`도 함께 관리해야 합니다.

---

## 3. 기술 스택

| 구분 | 사용 기술 |
| --- | --- |
| 프레임워크 | React 19 |
| 빌드 도구 | Vite 8 |
| 라우팅 | react-router-dom |
| 상태 관리 | Zustand |
| 스타일 | CSS Modules + 전역 CSS 변수 |
| API 통신 | fetch |
| 환경변수 | Vite `import.meta.env` |

---

## 4. 실행 방법

### 4.1 패키지 설치

```bash
cd frontend
npm install
```

### 4.2 환경변수

`frontend/.env`(gitignore)를 만들고 `VITE_API_BASE_URL`(백엔드 서버 주소)를 설정합니다.

백엔드 주소는 코드에 하드코딩하지 말고 항상 `.env`의 `VITE_API_BASE_URL`을 사용합니다. (값은 팀에서 공유)

### 4.4 개발 서버 실행

```bash
npm run dev
```

기본 주소:

```text
http://localhost:5173
```

---

## 5. 권장 폴더 구조

현재 프론트는 아래 구조를 기준으로 관리합니다.

```text
frontend/
├── public/
├── src/
│   ├── api/
│   │   ├── health.js
│   │   ├── stories.js
│   │   ├── characters.js
│   │   ├── voice.js
│   │   ├── scenes.js
│   │   └── render.js
│   ├── assets/
│   ├── components/
│   ├── mocks/
│   ├── pages/
│   │   ├── home/
│   │   ├── story-input/
│   │   ├── scene-check/
│   │   ├── character/
│   │   ├── scene-editor/
│   │   ├── timeline/
│   │   └── export/
│   ├── store/
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css
├── .env                  # 로컬 환경변수(gitignore). VITE_API_BASE_URL 등
├── package.json
└── README.md
```

### 폴더 역할

| 폴더 | 역할 |
| --- | --- |
| `src/pages/` | 화면 단위 컴포넌트 |
| `src/components/` | 공통 UI 컴포넌트 |
| `src/api/` | 백엔드 API 호출 함수 |
| `src/store/` | 전역 상태 관리 |
| `src/mocks/` | 화면 개발용 임시 데이터 |
| `src/assets/` | 이미지, 아이콘 등 정적 리소스 |

---

## 6. 화면 라우팅 기준

몽실책방의 기본 화면 흐름은 다음과 같습니다.

```text
/                  → 홈 / 내 작업
/story-input       → 스토리 입력
/scene-check       → 씬 확인·수정
/character         → 캐릭터 생성·라이브러리
/background        → 배경 생성·라이브러리
/scene-editor      → 씬 편집기 (배경↔씬 연결)
/voice             → 보이스 매핑 (나레이션·캐릭터에 보이스 연결, 보이스 라이브러리)
/timeline          → 타임라인
/export            → 렌더링·다운로드
```

### `/voice` 보이스 매핑 페이지

- 2단 레이아웃: **왼쪽**(연결 대상 = 나레이션 + 등장 캐릭터), **오른쪽**(보이스 라이브러리 + 생성 폼).
- 보이스는 **Voice Library 자산**으로 관리한다. 나레이션은 `story.narratorVoiceId`, 캐릭터는 `character.voiceId`를 사용한다.
- 등장 캐릭터는 `story.scenes[].items[]`의 dialogue `speaker`를 중복 없이 추출해 저장된 캐릭터와 **name 기준 매칭**한다. 매칭 안 되면 "저장된 캐릭터 없음" 안내.
- 기본 narrator preset 4개(`isPreset=true`)는 **수정/삭제 버튼을 숨긴다.** 나레이션엔 `voiceType="narrator"`, 캐릭터엔 `voiceType="character"` 보이스만 연결 버튼이 활성화된다.
- `sampleAudioUrl`이 있으면 미리듣기(audio), 없으면 **"샘플 준비 중"(비활성)**. 실제 샘플·클로닝·TTS 합성은 AI 단계라 프론트는 다루지 않는다.
- 프론트는 `provider`/`model`을 입력/표시하지 않고, **AI/TTS 서버를 직접 호출하지 않으며 FastAPI 백엔드만** 호출한다.
- 진입: `/voice?storyId=story_mock_001`처럼 query param이 있으면 자동 선택, 없으면 스토리 드롭다운(`GET /api/stories`)에서 선택.

프론트 화면 흐름은 아래 순서를 우선 유지합니다.

```text
스토리 입력
→ 씬 확인
→ 캐릭터 선택/생성
→ 보이스 클로닝 또는 목소리 선택
→ 씬 편집
→ 타임라인
→ 출력
```

---

## 7. 디자인 시스템 규칙

프론트 컴포넌트는 `DESIGN.md`의 디자인 시스템을 따릅니다.

### 7.1 색상

색상은 직접 하드코딩하지 말고 `src/index.css`에 정의된 CSS 변수를 사용합니다.

```css
var(--bg)
var(--text)
var(--text-h)
var(--border)
var(--code-bg)
var(--accent)
var(--accent-bg)
var(--accent-border)
```

### 7.2 버튼

기본 버튼 역할은 다음 기준을 따릅니다.

| 버튼 | 용도 |
| --- | --- |
| Primary | 다음 단계, 생성, 저장 |
| Secondary | 이전, 취소 |
| Ghost | 카드 내부 보조 액션 |

### 7.3 카드

씬 카드, 캐릭터 카드, 음성 카드, 결과 카드 모두 같은 카드 패턴을 사용합니다.

```css
.card {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
}
```

### 7.4 빈 상태

데이터가 없을 때 mock을 무조건 보여주지 말고, 사용자가 다음 행동을 할 수 있는 안내를 표시합니다.

예시:

```text
스토리를 먼저 입력해주세요.
[스토리 입력으로 돌아가기]
```

---

## 8. 상태 관리 기준

상태 관리는 화면별 local state와 전역 store를 구분해서 사용합니다.

### 8.1 Story Store

스토리 입력과 씬 확인에서 사용하는 상태입니다.

```js
{
  storyId: null,
  storyTitle: '',
  storyText: '',
  scenes: [],
  isParsing: false,
  parseError: null
}
```

### 8.2 Scene 구조

백엔드 Story Parse API 응답 구조를 그대로 사용합니다.

```js
{
  sceneId: 'scene_001',
  order: 1,
  items: [
    {
      type: 'narration',
      speaker: null,
      text: '어린 왕자는 작은 별에 혼자 살았어요.',
    },
    {
      type: 'dialogue',
      speaker: '어린왕자',
      text: '오늘은 어디로 여행을 떠나볼까?',
    },
  ],
}
```

주의:

```text
scene.id 사용하지 않기
scene.segments 사용하지 않기
scene.sceneId 사용하기
scene.items 사용하기
```

### 8.3 Character Store

캐릭터 라이브러리와 캐릭터 선택에서 사용하는 상태입니다.

```js
{
  characters: [
    {
      characterId: 'char_mock_001',
      name: '어린왕자',
      appearancePrompt: '금발 단발, 초록 외투, 작은 소년', // ComfyUI 생성용
      description: '호기심 많고 다정한 어린 왕자',          // 표시용 메타(선택)
      imageUrl: '/storage/characters/char_mock_001.png',  // ComfyUI 생성 결과(미완료 시 null)
      voiceId: 'voice_mock_001',                          // 연결된 보이스(없으면 null)
    },
  ],
  selectedCharacterId: null
}
// seed / referenceImageUrl / stylePreset / lockProfile / voiceProfile 은 백엔드가 받지 않는다(ComfyUI/AI 파트 관리).
```

### 8.4 Voice Store

TTS와 보이스 클로닝에서 사용하는 상태입니다.

```js
{
  narratorVoiceId: 'narrator_default',

  voiceProfiles: [
    {
      voiceId: 'voice_001',
      characterId: 'char_001',
      name: '어린왕자 목소리',
      type: 'cloned',
      sampleFileName: 'prince_sample.wav',
      status: 'ready',
    },
  ],

  sceneVoiceAssets: {
    scene_001: [
      {
        itemIndex: 0,
        type: 'narration',
        speaker: null,
        text: '어린 왕자는 작은 별에 혼자 살았어요.',
        voiceId: 'narrator_default',
        audioUrl: '/static/audio/scene_001_item_000.wav',
        durationSec: 3.2,
        status: 'ready',
      },
      {
        itemIndex: 1,
        type: 'dialogue',
        speaker: '어린왕자',
        text: '오늘은 어디로 여행을 떠나볼까?',
        voiceId: 'voice_001',
        audioUrl: '/static/audio/scene_001_item_001.wav',
        durationSec: 2.4,
        status: 'ready',
      },
    ],
  },
}
```

### 8.5 Render Store

렌더링 단계에서 사용하는 상태입니다.

```js
{
  renderJobId: null,
  renderStatus: 'idle',
  progress: 0,
  resultVideoUrl: null,
  renderError: null
}
```

---

## 9. Story Parse API 연동

현재 백엔드에 구현된 Story Parse API는 다음과 같습니다.

```text
POST /api/stories/parse
```

### 9.1 요청

```json
{
  "title": "새 동화",
  "script": "어린 왕자는 작은 별에 혼자 살았어요.\n어린왕자: \"오늘은 어디로 여행을 떠나볼까?\""
}
```

현재 제목 입력 UI가 없다면 `title`은 임시로 `"새 동화"`를 사용해도 됩니다.

### 9.2 응답

```json
{
  "storyId": "story_mock_001",
  "title": "새 동화",
  "scenes": [
    {
      "sceneId": "scene_001",
      "order": 1,
      "items": [
        {
          "type": "narration",
          "speaker": null,
          "text": "어린 왕자는 작은 별에 혼자 살았어요."
        },
        {
          "type": "dialogue",
          "speaker": "어린왕자",
          "text": "오늘은 어디로 여행을 떠나볼까?"
        }
      ]
    }
  ]
}
```

### 9.3 파싱 규칙

프론트는 대본을 직접 파싱하지 않습니다.

백엔드 파싱 규칙은 다음과 같습니다.

```text
빈 줄 = scene 구분
화자: "대사" = dialogue
그 외 문장 = narration
```

프론트는 사용자가 입력한 값을 그대로 백엔드에 보내고,  
백엔드 응답의 `scenes`를 화면에 표시합니다.

---

## 10. Story Parse API 함수

추천 파일:

```text
src/api/stories.js
```

예시:

```js
const BASE_URL = import.meta.env.VITE_API_BASE_URL

export async function parseStory({ title, script }) {
  const res = await fetch(`${BASE_URL}/api/stories/parse`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title, script }),
  })

  if (!res.ok) {
    throw new Error(`스토리 파싱 실패: HTTP ${res.status}`)
  }

  return res.json()
}
```

---

## 11. StoryInputPage 구현 기준

스토리 입력 화면은 사용자가 대본을 입력하고 “씬 분해하기”를 누르는 화면입니다.

### 입력 안내 문구

```text
내레이션과 대사를 입력하세요.
대사는 화자: "대사" 형식으로 써주세요.
장면을 나누고 싶으면 빈 줄을 넣어주세요.
```

### 버튼 흐름

```text
씬 분해하기 클릭
→ POST /api/stories/parse 호출
→ storyId, title, scenes 저장
→ /scene-check 이동
```

### 로딩 처리

API 호출 중에는 버튼을 비활성화합니다.

```text
분석 중...
```

### 에러 처리

```text
스토리 분석에 실패했습니다. 백엔드 서버가 실행 중인지 확인해주세요.
```

---

## 12. SceneCheckPage 구현 기준

씬 확인 화면은 백엔드에서 분해한 scene 목록을 보여주는 화면입니다.

```jsx
{scenes.map((scene) => (
  <li key={scene.sceneId}>
    <span>씬 {scene.order}</span>

    {scene.items.map((item, index) => (
      <p key={index}>
        <span>
          {item.type === 'dialogue' ? item.speaker : '내레이션'}
        </span>
        {item.text}
      </p>
    ))}
  </li>
))}
```

### 빈 상태

`scenes`가 비어 있으면 mock을 보여주지 말고 다음 안내를 표시합니다.

```text
스토리를 먼저 입력해주세요.
[스토리 입력으로 돌아가기]
```

---

## 13. TTS 기능 기준

TTS는 현재 개발 범위입니다.

TTS는 씬 item을 음성 파일로 변환하는 기능입니다.  
프론트는 실제 TTS 모델을 실행하지 않고, 백엔드 API를 호출해 결과를 받습니다.

### 13.1 TTS 대상

TTS 대상은 `scene.items`입니다.

```text
scene.items의 narration → 내레이터 음성
scene.items의 dialogue → 해당 speaker 캐릭터 음성
```

프론트는 `scene.items`를 다시 파싱하지 않습니다.

### 13.2 음성 선택 기준

| item type | speaker | voiceId |
| --- | --- | --- |
| `narration` | `null` | `narratorVoiceId` |
| `dialogue` | 캐릭터명 | 해당 캐릭터의 `voiceId` |

예시:

```text
narration → narrator_default
dialogue + speaker = "어린왕자" → char_001.voiceId
```

### 13.3 TTS API 기준안

현재 개발 기준 API입니다.  
백엔드 구현과 다르면 백엔드 확정 스펙에 맞춰 이 문서를 반드시 수정합니다.

```text
POST /api/voice/tts
```

요청 예시:

```json
{
  "storyId": "story_mock_001",
  "sceneId": "scene_001",
  "items": [
    {
      "itemIndex": 0,
      "type": "narration",
      "speaker": null,
      "text": "어린 왕자는 작은 별에 혼자 살았어요.",
      "voiceId": "narrator_default"
    },
    {
      "itemIndex": 1,
      "type": "dialogue",
      "speaker": "어린왕자",
      "text": "오늘은 어디로 여행을 떠나볼까?",
      "voiceId": "voice_001"
    }
  ]
}
```

응답 예시:

```json
{
  "sceneId": "scene_001",
  "audioItems": [
    {
      "itemIndex": 0,
      "audioUrl": "/static/audio/scene_001_item_000.wav",
      "durationSec": 3.2
    },
    {
      "itemIndex": 1,
      "audioUrl": "/static/audio/scene_001_item_001.wav",
      "durationSec": 2.4
    }
  ]
}
```

### 13.4 TTS 프론트 책임

```text
1. 씬별 TTS 대상 item 목록 표시
2. narration은 내레이터 음성으로 표시
3. dialogue는 speaker 이름과 연결된 캐릭터 음성으로 표시
4. TTS 생성 중 로딩 표시
5. 생성 완료 후 audioUrl, durationSec 저장
6. Timeline에서 durationSec을 scene 길이 계산에 반영
```

---

## 14. 보이스 클로닝 기능 기준

보이스 클로닝은 현재 개발 범위입니다.

보이스 클로닝은 사용자가 업로드한 음성 샘플을 기반으로  
캐릭터 전용 목소리를 만들고, 그 결과를 캐릭터 라이브러리에 저장하는 기능입니다.

중요한 점은 다음과 같습니다.

```text
보이스 클로닝 결과는 voiceId로 끝나면 안 된다.
반드시 characterId와 연결되어야 한다.
캐릭터 재사용 시 외형 정보와 voiceId를 함께 불러와야 한다.
```

### 14.1 사용 흐름

```text
캐릭터 생성 또는 선택
→ 음성 샘플 업로드
→ 보이스 클로닝 요청
→ voiceId 발급
→ characterId와 voiceId 연결
→ 캐릭터 라이브러리에 외형+목소리 저장
→ 다른 스토리에서 같은 캐릭터와 목소리 재사용
```

### 14.2 보이스 클로닝 API 기준안

현재 개발 기준 API입니다.  
백엔드 구현과 다르면 백엔드 확정 스펙에 맞춰 이 문서를 반드시 수정합니다.

```text
POST /api/voice/clone
```

요청 방식은 파일 업로드가 필요하므로 `multipart/form-data`를 사용합니다.

필드 예시:

```text
characterId: char_001
voiceName: 어린왕자 목소리
sampleFile: 사용자가 업로드한 wav/mp3 파일
```

응답 예시:

```json
{
  "voiceId": "voice_001",
  "characterId": "char_001",
  "name": "어린왕자 목소리",
  "type": "cloned",
  "status": "ready"
}
```

### 14.3 보이스 클로닝 프론트 책임

프론트는 다음을 처리합니다.

```text
1. 음성 샘플 파일 선택
2. 업로드 전 파일명, 크기, 확장자 표시
3. characterId와 함께 clone 요청
4. 생성 중 상태 표시
5. 성공 시 반환된 voiceId를 해당 캐릭터에 연결
6. 캐릭터 카드에 "목소리 있음" 상태 표시
7. 다른 스토리에서 해당 캐릭터를 불러올 때 voiceId도 함께 사용
```

### 14.4 파일 업로드 UI 기준

업로드 가능한 파일 형식은 백엔드 기준을 따릅니다.  
프론트에서는 최소한 아래 안내를 표시합니다.

```text
WAV 또는 MP3 음성 샘플을 업로드해주세요.
잡음이 적고 5초 이상인 음성을 권장합니다.
```

---

## 15. CharacterPage 구현 기준

> **✅ 현재 구현 상태 (백엔드 Character Job API 연동 완료)**
> - `CharacterPage`는 백엔드 Character Job API와 연동된다. (생성→Job 조회→목록 동기화, 수정, 삭제, 선택)
> - 캐릭터는 `useCharacterStore`에서 **전역 캐시**로 관리한다. 최종 저장소는 백엔드이며, 페이지 진입 시 `GET /api/characters`로 동기화한다.
> - 프론트는 **ComfyUI를 직접 호출하지 않는다.** 항상 `프론트 → FastAPI 백엔드 → AI/ComfyUI` 구조를 따른다.
> - 현재 캐릭터 스키마는 `characterId`, `name`, `appearancePrompt`, `imageUrl`이다. 기존 `locked`, `tags`, `image_url` 구조는 사용하지 않는다.
> - `imageUrl`이 `null`이면 "이미지 준비 중" placeholder를 표시한다.
> - 생성 Job은 **비동기**다. `generate`가 `jobId`(`pending`)를 반환하면 `utils/pollJob.js`로 `completed/failed`까지 폴링한다. (`api/jobs.js`의 `getJob` 공통 사용)
> - `CharacterPage`는 조립만 담당하고, 실제 UI는 컴포넌트로 분리되어 있다:
>   `components/characters/CharacterCreateForm.jsx`, `CharacterList.jsx`, `CharacterCard.jsx`, `CharacterEditForm.jsx`
>   (공용 스타일은 `pages/character/CharacterPage.module.css` 모듈을 공유)
> - 관련 파일: `src/api/characters.js`, `src/utils/apiError.js`, `src/store/useCharacterStore.js`
> - 카드의 수정/삭제 버튼은 디자인 확정 전 **임시 UI**이며, 기존 CSS 톤(`var(--*)`)을 따른다.
> - 생성 폼은 입력이 비면 버튼 비활성화 + 그 이유를 안내하는 visible validation 메시지를 보여준다.
> - ⚠️ 캐릭터/배경의 "AI 서버 연결 확인" 임시 버튼은 외부 AI 서버 연동 완료로 **제거됐다.** 연결 확인 컴포넌트(`components/AiConnectionCheck.jsx`, `src/api/ai.js`, `.aiCheck`)는 현재 **보이스(VoicePage)에서만** 임시로 사용 중이며, TTS 실연동 후 제거 예정 — 제거 체크리스트: 루트 [`TEMP_AI_CONNECTION_TEST.md`](../TEMP_AI_CONNECTION_TEST.md)
> - 아래 본문(목소리/보이스 클로닝 등)은 이후 단계 설계이며 이번 작업 범위가 아니다.

캐릭터 화면은 단순히 캐릭터 이미지만 다루는 화면이 아닙니다.

캐릭터 화면은 다음 기능을 포함합니다.

```text
1. 캐릭터 생성
2. 캐릭터 라이브러리 목록
3. 캐릭터 선택
4. 캐릭터 외형 정보 확인
5. 캐릭터 목소리 선택
6. 보이스 클로닝 샘플 업로드
7. characterId와 voiceId 연결
```

### 캐릭터 카드 표시 권장 정보

```text
캐릭터 이름
캐릭터 썸네일
외형 프롬프트 요약
목소리 상태: 기본 / 클로닝됨 / 없음
선택 버튼
목소리 만들기 버튼
```

### 캐릭터 재사용 시 필수 상태

캐릭터를 다른 스토리에서 불러올 때는 아래 정보가 함께 있어야 합니다.

```js
{
  characterId: 'char_001',
  name: '어린왕자',
  imageUrl: '/static/characters/char_001.png',
  appearancePrompt: '금발 단발, 초록 외투, 작은 소년',
  seed: 1024,
  voiceId: 'voice_001',
}
```

---

## 15.5 BackgroundPage 구현 기준 (✅ 백엔드 Background API 연동 완료)

> - 라우트 `/background` (`App.jsx`, `NavBar`에 "배경" 추가). 배경 상태는 **`useBackgroundStore`**(캐릭터와 별도 store).
> - **배경은 2단계 구조**: `후보(candidateId, 임시)` → 1장 선택 저장 → `배경(backgroundId, 라이브러리)`. **씬에는 candidateId가 아니라 backgroundId만** 연결한다.
> - **역할 분리**: BackgroundPage는 배경 **라이브러리(생성/저장/수정/삭제)** 만 담당한다. **씬 ↔ 배경 연결은 Scene Editor(`/scene-editor`)** 가 담당한다 (씬별로 라이브러리의 배경을 골라 `PATCH /api/scenes/{sceneId}/background` 호출). 캐릭터도 같은 방식으로 추후 Scene Editor에서 배정한다.
> - **promptInput만 전송**: `generate`에는 사용자가 수정한 **`promptInput`만** 보낸다. `count`도 보내지 않는다(개수는 백엔드/ComfyUI 결정).
> - **finalPrompt 미리보기는 실시간 계산(전송 X)**: store는 백엔드가 붙이는 suffix(배경 규칙)만 `promptSuffix`로 보관하고, 미리보기는 항상 **`현재 promptInput + promptSuffix`** 로 계산한다 → 프롬프트를 수정하면 미리보기도 즉시 갱신(stale 방지). 실제 finalPrompt 조립은 백엔드가 한다. (백엔드 suffix를 프론트에 하드코딩하지 않음 — 추천 응답에서 추출)
> - **초기 로딩 실패는 에러로 표시**: `getBackgrounds`/`getStories` 실패를 "빈 목록"으로 숨기지 않고, "불러오지 못했습니다 …" 에러 메시지로 보여준다(백엔드 다운과 데이터 없음을 구분). BackgroundPage·`StorySceneSelect`·SceneEditor 모두 동일.
> - 프론트는 **ComfyUI를 직접 호출하지 않는다.** `프론트 → FastAPI 백엔드` 만.
> - `imageUrl`이 `null`이면 "이미지 준비 중" placeholder.
> - 컴포넌트 분리: `components/backgrounds/`의 `BackgroundPromptPanel`, `BackgroundCandidateGrid`, `BackgroundCandidateCard`, `BackgroundSaveForm`, `BackgroundLibrary`, `BackgroundCard`, `StorySceneSelect`(스토리/씬 드롭다운) (공용 스타일 `pages/background/BackgroundPage.module.css`).
> - 관련 파일: `src/api/backgrounds.js`, `src/store/useBackgroundStore.js`, `src/utils/apiError.js`(배경/스토리/씬 메시지 추가).
> - storyId/sceneId는 **`GET /api/stories` 기반 드롭다운**(`StorySceneSelect`)으로 고른다(ID 직접 입력 X). 나중에 props/route state로 주입할 수 있게 store에 분리해 둠.

---

## 16. TimelinePage 구현 기준

타임라인은 단순히 씬 순서만 보여주는 화면이 아닙니다.

타임라인은 씬 이미지, 음성 길이, 자막을 기준으로 최종 영상 길이를 정리하는 화면입니다.

### 타임라인에서 필요한 정보

```text
sceneId
order
thumbnailUrl
durationSec
audioDurationSec
subtitleText
voiceAssets
```

### 길이 계산 기준

TTS 결과가 있다면 씬 길이는 음성 길이를 기준으로 보정합니다.

```text
finalDurationSec = max(userDurationSec, audioDurationSec + 0.4)
```

프론트에서는 이 계산 결과를 표시하고, 최종 확정 값은 백엔드 렌더링 API가 다시 검증할 수 있습니다.

---

## 17. ExportPage 구현 기준

Export 화면은 최종 영상 렌더링 상태를 보여주는 화면입니다.

렌더링 전 확인해야 할 정보:

```text
storyId
scenes
selected characters
voiceAssets
subtitle text
timeline durations
```

음성 생성이 필요한 씬이 남아 있으면 사용자에게 안내합니다.

```text
아직 음성이 생성되지 않은 장면이 있습니다.
먼저 음성을 생성해주세요.
```

---

## 18. API 파일 분리 원칙

API 호출 함수는 화면 컴포넌트 안에 직접 작성하지 않습니다.

```text
src/api/health.js
src/api/stories.js
src/api/characters.js
src/api/voice.js
src/api/scenes.js
src/api/render.js
```

### `src/api/characters.js` 역할 (✅ 백엔드 연동 완료)

캐릭터 생성은 **비동기 Job**입니다. `generate`는 `jobId`(`status="pending"`)를 반환하고, `utils/pollJob.js`로 `running`→`completed/failed`까지 폴링합니다. ComfyUI 실제 생성은 백그라운드에서 진행되며, `completed`면 캐릭터 목록을 다시 불러옵니다.

```js
export async function generateCharacter({ name, appearancePrompt }) {
  // POST /api/characters/generate  -> { jobId, status, message }
}

export async function getJob(jobId) {
  // GET /api/jobs/{jobId}  -> { jobId, type, status, progress, result, error }
}

export async function listCharacters() {
  // GET /api/characters  -> [{ characterId, name, appearancePrompt, imageUrl }]
}

export async function createCharacter({ name, appearancePrompt, imageUrl = null }) {
  // POST /api/characters  -> { characterId, name, appearancePrompt, imageUrl }
}

export async function getCharacter(characterId) {
  // GET /api/characters/{characterId}  (404 시 없음)
}

export async function updateCharacter(characterId, patch) {
  // PATCH /api/characters/{characterId}  (name/appearancePrompt/imageUrl 부분 수정)
}

export async function deleteCharacter(characterId) {
  // DELETE /api/characters/{characterId}  -> { deleted, characterId }
}
```

> 캐릭터 데이터: `{ characterId, name, appearancePrompt, description, imageUrl, voiceId }` — `imageUrl`은 ComfyUI 비동기 생성 결과(완료 전 `null`), `voiceId`는 연결된 보이스(없으면 `null`). 스타일/seed/reference/lock 등은 백엔드가 받지 않습니다(ComfyUI 파트 담당).

### `src/api/voice.js` 역할

```js
export async function cloneVoice({ characterId, voiceName, sampleFile }) {
  // POST /api/voice/clone
}

export async function generateSceneVoice({ storyId, sceneId, items }) {
  // POST /api/voice/tts
}
```

실제 API 경로와 요청/응답 구조가 백엔드와 달라지면 이 문서와 `src/api/voice.js`를 함께 수정합니다.

---

## 19. Mock 처리 기준

프론트 mock은 화면 확인용입니다.

백엔드 API가 준비된 기능은 실제 API 응답을 우선 사용합니다.

```text
Story Parse → 실제 API 사용
Health Check → 실제 API 사용
TTS / Voice Cloning → 개발 중 API 기준에 맞춰 연결
```

mock이 실제 API 응답을 가리면 안 됩니다.

잘못된 예:

```text
API 호출 성공 후에도 mock scenes를 화면에 표시
```

올바른 예:

```text
API 호출 성공 → 응답 data를 store에 저장 → store 기준으로 화면 표시
```

---

## 20. 로딩 / 에러 처리 기준

모든 API 호출에는 로딩과 에러 상태가 있어야 합니다.

### Story Parse

```text
분석 중...
스토리 분석에 실패했습니다. 백엔드 서버가 실행 중인지 확인해주세요.
```

### TTS

```text
음성 생성 중...
음성 생성에 실패했습니다. 다시 시도해주세요.
```

### Voice Cloning

```text
목소리 클로닝 중...
보이스 클로닝에 실패했습니다. 음성 파일과 백엔드 상태를 확인해주세요.
```

### Render

```text
영상 렌더링 중...
영상 렌더링에 실패했습니다.
```

---

## 21. 파일 업로드 기준

보이스 클로닝에서 파일 업로드가 필요합니다.

프론트는 파일을 base64로 직접 변환해 보내지 말고,  
백엔드가 요구하는 경우 `FormData`를 사용합니다.

```js
const formData = new FormData()
formData.append('characterId', characterId)
formData.append('voiceName', voiceName)
formData.append('sampleFile', sampleFile)
```

---

## 22. 문서 최신화 규칙

프론트 코드가 바뀌면 관련 문서도 함께 수정합니다.

특히 아래가 바뀌면 `frontend/README.md`를 반드시 최신화합니다.

```text
라우팅 구조
상태 구조
API 경로
API 요청/응답 구조
Story Parse 응답 구조
TTS 요청/응답 구조
보이스 클로닝 요청/응답 구조
Character Store 구조
Voice Store 구조
Timeline 데이터 구조
```

---

## 23. 금지사항

프론트에서 하지 말아야 할 일은 다음과 같습니다.

```text
AI 모델 직접 실행 금지
ComfyUI 직접 호출 금지
TTS 모델 직접 실행 금지
보이스 클로닝 모델 직접 실행 금지
대본을 프론트에서 직접 파싱 금지
백엔드 URL 하드코딩 금지
API 호출 코드를 페이지 컴포넌트에 직접 작성 금지
백엔드 응답을 mock 데이터로 덮어쓰기 금지
scene.id / scene.segments 기준 사용 금지
```

---

## 24. 개발 우선순위

프론트 개발 우선순위는 다음과 같습니다.

```text
1. Health Check 연결 유지
2. Story Parse API 연결
3. SceneCheckPage를 sceneId/items 기준으로 정리
4. CharacterPage에서 캐릭터 선택/생성 상태 정리
5. Voice Cloning UI 및 voiceId-characterId 연결
6. TTS 생성 UI 및 scene.items 기반 음성 요청
7. Timeline에서 voiceAssets와 durationSec 반영
8. Export에서 음성/자막/렌더링 상태 확인
```

---

## 25. 완료 기준

현재 프론트 작업의 완료 기준은 다음과 같습니다.

```text
스토리 입력 화면에서 대본 입력
→ 씬 분해하기 클릭
→ POST /api/stories/parse 호출
→ storyId, scenes 저장
→ scene-check 화면에서 sceneId/items 기준 표시
→ 캐릭터 선택/생성 화면에서 voiceId 상태를 함께 관리
→ 보이스 클로닝 샘플 업로드 UI 제공
→ TTS 대상이 scene.items 기준으로 정리
→ Timeline/Export에서 음성 생성 여부와 durationSec을 사용할 수 있는 구조
```

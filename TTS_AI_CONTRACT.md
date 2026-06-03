# TTS 백엔드 ↔ AI/TTS 파트 요청·응답 계약

백엔드가 AI/TTS 파트에 **① 보이스 클로닝**과 **② 음성 합성**을 요청할 때의 **JSON 계약**이다.
(현재 백엔드는 `AI_TTS_URL`이 설정되어 있으면 이 계약으로 실제 AI/TTS 서버에 요청한다.
`AI_TTS_URL`이 없고 로컬 Qwen 설정도 없으면 합성 파일 없이 `audioUrl=null` 상태로 동작한다.)

> 역할 분리
> - **Story Parse**: 감정(emotion) 결정
> - **백엔드**: ① 보이스 자산(`voiceId`) 발급 + reference 오디오 저장 + 캐릭터/나레이션 연결, ② scene.items → 합성 대상(audio target) 구성(+ reference/emotion/character prompt 동봉), AI에 요청, 결과(`audioUrl`) 저장
> - **AI/TTS(김도연)**: ① 보이스 클로닝(`create_voice_clone_prompt` + voiceId별 캐시 + sample 반환), ② `text`를 emotion·voice로 합성해 `audioUrl` 반환  ← **이 두 가지가 AI 영역**

---

## 0. 모델 기준 — Qwen3-TTS 0.6B (ref_audio + ref_text)

Qwen3-TTS 0.6B-Base는 **`ref_audio` + `ref_text` 기반** voice clone이다. **`voiceId`만으로 모델이 목소리를 자동으로 찾지 못한다.**
같은 reference를 재사용할 땐 `create_voice_clone_prompt(ref_audio, ref_text)`로 **prompt feature**를 만들고 이후 그 `voice_clone_prompt`를 재사용한다.

**그래서 우리 서비스의 합의 구조:**
- **AI 서버가 `voiceId → voice_clone_prompt`를 캐싱**하면, 백엔드는 `voiceId`만으로 재사용 요청이 가능하다.
- 단 **cache miss(서버 재시작/캐시 비움) 대비**, 백엔드는 합성 요청에 **`referenceAudioUrl` + `referenceText`를 항상 함께** 보낸다.

**AI 서버 합성 처리 순서:**
1. `voiceId`로 `voice_clone_prompt` 캐시 조회
2. 캐시 있으면 그대로 사용
3. 캐시 없으면 `referenceAudioUrl` 다운로드 + `referenceText`로 `create_voice_clone_prompt` 재생성
4. 재생성한 prompt를 `voiceId` 기준으로 다시 캐시
5. `generate_voice_clone` 합성 실행

**preset 보이스 주의:** 기본 나레이터 preset(§1.1)은 사용자 reference가 없어 `referenceAudioUrl/referenceText`가 **null**일 수 있다. 이 경우 **AI 서버가 해당 preset `voiceId`의 기본 speaker/prompt를 자체 보유**해야 한다.

> **voiceId가 흐르는 길**
> `POST /api/voices`(보이스 자산 생성, voiceId 발급) → 연결 → `POST /api/tts/scene`(audio에 voiceId 복사) → AI는 그 voiceId의 목소리로 합성.
> - **dialogue**: `PATCH /api/characters/{id}/voice`로 캐릭터에 연결 → TTS가 speaker로 캐릭터 찾아 그 `voiceId` 복사.
> - **narration**: `PATCH /api/stories/{id}/narrator-voice`로 스토리에 연결 → TTS가 story의 `narratorVoiceId` 복사.
>
> **연결 제한 = `status=ready`만** (voiceType 아님). `voiceType`(narrator/character)은 추천 태그일 뿐 — narrator 추천 보이스도 캐릭터에, character 추천 보이스도 나레이션에 연결 가능. preset narrator 4개(§1.1)는 기본 나레이터로 쓰라고 제공되지만, 연결 자체에 타입 제한은 없다.

---

## 1. 보이스(Voice) 자산 — 클로닝 영역 (AI 역할 ①)

보이스는 캐릭터/배경처럼 **재사용 가능한 라이브러리 자산**이다. 백엔드가 `voiceId`를 발급하고, 실제 목소리(클로닝/모델)는 AI/TTS 파트가 그 `voiceId`에 매핑·관리한다.

### 1.0 보이스 클로닝 요청 (multipart — 실제 구현)

`POST {AI_VOICE_CLONE_URL}`  ·  `Content-Type: multipart/form-data`

| 필드 | 예 | 설명 |
|---|---|---|
| `audioFile` | reference.webm | 사용자 녹음/업로드 원본 (webm/wav/mp3/m4a) |
| `voiceId` | voice_mock_003 | 백엔드 발급 식별자 (캐시 키) |
| `voiceType` | character | narrator / character (추천 태그, 연결 제한 아님) |
| `characterId` | char_mock_001 또는 "" | (선택) 연결 캐릭터 |
| `referenceText` | "안녕하세요…" | 사용자가 따라 읽은 문장 (= ref_text) |
| `sampleText` | "이 목소리는 동화 속 캐릭터 대사에 사용됩니다." | 미리듣기 샘플 생성용 문장 |
| `voicePrompt` | "맑고 순수한 소년 목소리" | 원하는 목소리 의도 |
| `language` | Korean | |
| `provider` / `model` | qwen / Qwen3-TTS-12Hz-0.6B-Base | |

**AI가 할 일:** `create_voice_clone_prompt(ref_audio=audioFile, ref_text=referenceText)`로 prompt 생성 → **`voiceId` 기준 캐시** → `sampleText`로 짧은 미리듣기(sample) 합성 후 반환.

**응답(둘 다 방어 처리됨):**
- **A. 오디오 바이트 직접** — `Content-Type: audio/wav`, body = wav bytes
- **B. JSON(base64)** — `{ "sampleAudioBase64": "...", "durationSec": 3.2, "provider": "qwen", "model": "Qwen3-TTS-12Hz-0.6B-Base" }`

**백엔드 처리:** sample을 `storage/voices/{voiceId}/sample.wav`로 저장 → voice 갱신 `status=ready`, `sampleAudioUrl=/storage/voices/{voiceId}/sample.wav`, `provider=qwen`, `model=Qwen3-TTS-12Hz-0.6B-Base`. 실패 시 `status=failed` + `error` 저장.
(원본 reference는 `storage/voices/{voiceId}/reference.{ext}`에 보관 → 합성 cache miss 시 재사용. voice 삭제 시 폴더째 정리.)

**백엔드가 만들어 보관하는 보이스 자산** (`GET /api/voices`로 조회):

```json
{
  "voiceId": "voice_mock_001",
  "name": "따뜻한 소년 목소리",
  "description": "밝고 호기심 많은 소년 톤",
  "voicePrompt": "warm, curious young boy voice",
  "voiceType": "character",
  "isPreset": false,
  "status": "pending",
  "sampleAudioUrl": null
}
```

| 필드 | 주체 | 설명 |
|---|---|---|
| `voiceId` | 백엔드 | 자산 식별자(발급). **참조 키** |
| `name` / `description` / `voicePrompt` | 백엔드/사용자 | 원하는 목소리에 대한 메타·의도(캐릭터 `appearancePrompt`와 같은 성격) |
| `voiceType` / `isPreset` | 백엔드 | 추천 용도(narrator/character) / 시스템 기본 보이스 여부 |
| `provider` / `model` | **AI/TTS** | 클로닝에 쓴 제공자/모델 — **AI가 채운다.** 내부 보관용이라 `GET /api/voices` 응답엔 노출 안 함 |
| `sampleAudioUrl` | **AI/TTS** | 미리듣기 샘플 음성 URL — **AI가 채운다** |
| `status` | **AI/TTS** | 생성 직후 `"pending"`(클로닝 대기). 클로닝 완료 시 AI가 `"ready"` 등으로 갱신 (preset은 seed 시 `"ready"`) |

- 백엔드는 `voiceId` + 메타(name/description/voicePrompt/voiceType/isPreset)만 정한다. **"실제 목소리를 어떻게 만드는가"(provider/model/클로닝)는 AI 영역**이라 생성/수정 요청으로 받지 않는다.
- ⚠️ 현재 백엔드엔 AI가 클로닝 결과(provider/model/sampleAudioUrl/status)를 써넣는 **통로가 아직 없다.** 보이스 클로닝 연동 시, AI 결과를 보이스 자산에 반영하는 엔드포인트/콜백을 추가한다.

### 1.1 기본 나레이션 보이스 preset (AI가 샘플·클로닝 채울 대상)

백엔드가 **기본 나레이터 보이스 4개**를 고정 voiceId로 메모리 seed한다. narration은 화자가 없어 캐릭터로 못 붙으므로, 사용자가 이 중 하나를 골라 `story.narratorVoiceId`로 쓴다. 현재 mock 자산이라 `sampleAudioUrl=null`.

| 고정 voiceId | 이름 | voicePrompt(영문 의도) |
|---|---|---|
| `voice_preset_narrator_calm_001` | 차분한 나레이션 | calm, warm, gentle narrator voice for fairy tale storytelling |
| `voice_preset_narrator_bright_001` | 밝은 나레이션 | bright, friendly, cheerful narrator voice for children story |
| `voice_preset_narrator_soft_001` | 부드러운 나레이션 | soft, cozy, gentle storytelling voice |
| `voice_preset_narrator_serious_001` | 진지한 나레이션 | serious, calm, stable narrator voice |

**AI/TTS 파트가 할 일**: 위 4개 voiceId 각각에 대해 ① 실제 클로닝(provider/model/status), ② **짧은 미리듣기 샘플(2~3초) 합성 후 `sampleAudioUrl` 채우기.** 채워지면 프론트 미리듣기 버튼이 활성화된다.

---

## 2. 백엔드 → AI/TTS 합성 요청 (scene 단위, 배치) (AI 역할 ②)

`POST {AI_TTS_URL}/tts`  (엔드포인트 이름/경로는 AI 파트가 정함)

```json
{
  "storyId": "story_mock_001",
  "sceneId": "scene_001",
  "items": [
    {
      "audioId": "audio_mock_001",
      "itemIndex": 0,
      "type": "narration",
      "speaker": null,
      "text": "어린왕자는 조용히 별을 바라보았다.",
      "emotion": "calm",
      "emotionLabel": "잔잔함",
      "emotionPrompt": "Speak in a calm and gentle tone.",
      "voiceType": "narrator",
      "voiceId": "voice_preset_narrator_calm_001",
      "voiceName": "차분한 나레이션",
      "voicePrompt": "calm, warm, gentle narrator voice",
      "referenceAudioUrl": null,
      "referenceText": null,
      "characterId": null,
      "characterName": null,
      "characterPrompt": null
    },
    {
      "audioId": "audio_mock_002",
      "itemIndex": 1,
      "type": "dialogue",
      "speaker": "어린왕자",
      "text": "친구가 되려면 어떻게 해야 해?",
      "emotion": "curious",
      "emotionLabel": "호기심",
      "emotionPrompt": "Speak in a curious and gentle tone.",
      "voiceType": "character",
      "voiceId": "voice_mock_003",
      "voiceName": "엄마가 연기한 어린왕자",
      "voicePrompt": "맑고 순수한 소년 목소리",
      "referenceAudioUrl": "/storage/voices/voice_mock_003/reference.webm",
      "referenceText": "사용자가 따라 읽은 문장",
      "characterId": "char_mock_001",
      "characterName": "어린왕자",
      "characterPrompt": "순수하고 호기심 많은 소년"
    }
  ]
}
```

> **합성 시 AI 처리(§0 재확인):** `voiceId` 캐시 있으면 그 `voice_clone_prompt` 사용, 없으면 `referenceAudioUrl`(다운로드) + `referenceText`로 재생성 후 `voiceId` 기준 재캐시. preset처럼 `referenceAudioUrl=null`이면 AI가 그 preset voiceId의 기본 speaker/prompt를 자체 사용.
>
> **instruction 조합:** AI는 `voicePrompt`(목소리 의도) + `characterPrompt`(캐릭터 말투) + `emotionPrompt`(감정 지시문)를 조합해, **사용자 reference 목소리 특징은 유지하면서 캐릭터 분위기·감정에 맞게** `text`를 합성한다.

### emotionPrompt 매핑 (백엔드가 emotion 키 → 자연어 instruction)

| emotion | emotionPrompt |
|---|---|
| neutral | Speak in a natural and neutral tone. |
| calm | Speak in a calm and gentle tone. |
| happy | Speak in a bright and happy tone. |
| sad | Speak in a sad and quiet tone. |
| angry | Speak in an angry and strong tone. |
| scared | Speak in a nervous and scared tone. |
| excited | Speak in an excited and energetic tone. |
| friendly | Speak in a warm and friendly tone. |
| serious | Speak in a serious and focused tone. |
| curious | Speak in a curious and gentle tone. |

알 수 없는 emotion → `Speak in a natural and neutral tone.`(neutral) fallback.

### 필드 의미
| 필드 | 설명 |
|---|---|
| `audioId` | **상관관계 키.** 응답에 그대로 돌려줘야 백엔드가 매칭한다. |
| `text` | **합성할 문장.** 이걸 음성으로 만든다. |
| `emotion` | 감정 스타일 키(영문). (`emotionLabel`은 표시용) |
| `emotionPrompt` | **감정 지시문(자연어).** 백엔드가 emotion 키→매핑. Qwen 합성 instruction으로 사용 |
| `voiceType` | `narrator`(내레이션) / `character`(대사) — 추천 태그(연결 제한 아님) |
| `voiceId` | **§1의 보이스 자산 ID(캐시 키).** 없으면 null → `voiceType` 기준 기본 목소리. 출처: dialogue=매칭 캐릭터 `voiceId`, narration=story `narratorVoiceId` |
| `voiceName` / `voicePrompt` | 보이스 이름 / 원하는 목소리 의도 |
| `referenceAudioUrl` | **ref_audio (cache miss 시 prompt 재생성용).** `/storage/...` URL. preset/미연결이면 null |
| `referenceText` | **ref_text (cache miss 시 재생성용).** preset/미연결이면 null |
| `speaker` | 대사의 화자명 (narration이면 null) |
| `characterId` | dialogue `speaker`로 매칭된 캐릭터 ID. narration/미매칭이면 null (매칭 키 = speaker == 캐릭터 name) |
| `characterName` | 매칭 캐릭터 이름 (narration/미매칭이면 null) |
| `characterPrompt` | **캐릭터 말투 prompt.** 백엔드 우선순위: `description` → `appearancePrompt` → name 기반 기본문. narration/미매칭이면 null |
| `itemIndex` | 원본 scene.items 인덱스 (참고용, 재번호 안 함) |

### enum 값
- `emotion`: `neutral · calm · happy · sad · angry · scared · excited · friendly · serious` (+ story-parse가 내는 추가 키는 emotionPrompt에서 neutral fallback)
- `voiceType`: `narrator · character`

---

## 3. AI/TTS → 백엔드 응답

AI는 **`audioId` → `audioUrl` 매핑만** 돌려주면 된다. (나머지 메타데이터는 백엔드가 이미 보관)

```json
{
  "storyId": "story_mock_001",
  "sceneId": "scene_001",
  "audios": [
    {
      "audioId": "audio_mock_001",
      "audioUrl": "https://.../audio_mock_001.wav",
      "durationSec": 3.2,
      "error": null
    },
    {
      "audioId": "audio_mock_002",
      "audioUrl": "https://.../audio_mock_002.wav",
      "durationSec": 0.8,
      "error": null
    }
  ]
}
```

### 응답 필드
| 필드 | 설명 |
|---|---|
| `audioId` | 요청에서 받은 값 그대로 (매칭 키) |
| `audioUrl` | 생성된 음성 파일 URL. 실패 시 `null` |
| `durationSec` | (선택) 음성 길이(초). 타임라인/자막 동기화에 유용. 없어도 됨 |
| `error` | (선택) 해당 item 실패 사유. 성공이면 `null` |

- **부분 실패 허용**: 한 item이 실패해도 전체를 막지 말고, 그 item만 `audioUrl: null, error: "..."`로 반환.

---

## 4. 동기 / 비동기

AI 파트가 자유롭게 선택한다.

- **동기**: 위 응답을 바로 반환.
- **비동기**: `jobId`를 먼저 주고 콜백/폴링으로 위 `audios` 형태를 전달.

백엔드는 받은 `audioUrl`을 해당 `audioId`의 `TTSAudio.audioUrl`에 채우기만 하면 된다.

---

## 5. 핵심 요약 (3줄)
1. **보이스 자산**: 백엔드가 `voiceId`+메타를 발급 → AI가 그 voiceId에 실제 목소리를 **클로닝**(provider/model/sampleAudioUrl/status 채움).
2. **합성**: 백엔드가 scene 단위 `items`(text + emotion + voiceType + voiceId + audioId)를 보내면, AI가 각 item을 합성해 **`audioId`마다 `audioUrl`**을 돌려준다.
3. **감정 = `emotion`(영문 키, 문장별), 목소리 = `voiceId`(dialogue=캐릭터 / narration=story.narratorVoiceId) / 없으면 `voiceType` 기본.**

---

## 참고: 현재 백엔드 상태

- **보이스 라이브러리**: `POST/GET/PATCH/DELETE /api/voices` 구현됨(mock). voiceId 발급·메타 저장만 하고 클로닝 결과(provider/model/sampleAudioUrl/status)는 비워둔다.
- **캐릭터 연결**: `PATCH /api/characters/{id}/voice`로 캐릭터에 voiceId 연결(보이스 삭제 시 참조 캐릭터 voiceId는 null 캐스케이드).
- **TTS**: `POST /api/tts/scene`은 audio target을 만들고 `AI_TTS_URL`이 있으면 `{AI_TTS_URL}/tts`로 요청한다. dialogue speaker→캐릭터(name 매칭)→characterId/voiceId 복사는 **이미 동작**한다(목소리 참조까지 흐름, 합성은 AI/TTS 서버).
- `AI_TTS_URL`이 없고 `QWEN_TTS_ENABLED=1`이면 로컬 Qwen fallback을 사용한다. 둘 다 없으면 합성 파일 없이 `audioUrl=null`로 남는다.

> **한 줄 요약:** AI 서버가 받을 수 있는 형태로 **데이터 포장(payload 구성)·결과 저장 구조까지는 끝났다.** 이제 실제 목소리를 만드는 것은 **AI 서버 연결 후** 가능하다.
- 백엔드 TTS/Voice 구조·필드 상세는 `backend/README.md`의 "TTS(음성 생성) API" / "보이스(Voice) 라이브러리" 참고.

---

## Remote ComfyUI TTS adapter URL rule

When the AI/TTS process runs on a different PC from the backend, `audioUrl`
must be playable from the teammate's browser. Prefer returning an absolute URL:

```json
{
  "audioId": "audio_mock_001",
  "audioUrl": "http://192.168.0.23:8100/view?filename=tts_xxx.wav&type=output",
  "durationSec": 3.2,
  "error": null
}
```

The bundled `ai.voice.tts_server` is a ComfyUI adapter for this contract. It
receives `POST /tts`, queues the configured ComfyUI voice workflow, then returns
an adapter-hosted URL such as `/view?...` or `/tts-output/tts_xxx.wav`.

Keep the backend unchanged: the remote TTS adapter should return an absolute
`audioUrl` by using `AI_TTS_PUBLIC_BASE_URL` or the incoming request base URL.
Do not rely on the backend to rewrite a relative URL.

For ComfyUI workflows that need engine-specific voice inputs, the adapter can
translate backend `voiceId` into values like `speaker`, `refAudio`, or `refText`
through `COMFYUI_TTS_VOICE_MAP_PATH`. The backend still sends the stable
contract fields; only the shared PC adapter owns this ComfyUI-specific mapping.

## 6. 통합 테스트 체크리스트 (AI 서버 연결 후)

### 6.1 지금 당장(연결 전) 점검해두면 좋은 것
- [ ] AI 서버가 백엔드의 `/storage/...` URL(`referenceAudioUrl`)에 **HTTP로 접근 가능한지** 확인. 불가하면 후속으로 TTS 요청도 multipart/base64 reference 동봉 방식으로 전환.
- [ ] `AI_VOICE_CLONE_URL` / `AI_TTS_URL`을 `.env`로 주입(코드 하드코딩 금지).
- [ ] AI 응답의 `audioId→audioUrl`이 `TTSAudio`에 저장되는지(이미 `apply_ai_result` 구현 — 응답 형식만 맞으면 됨).
- [ ] AI 응답에 `durationSec`이 오면 → 추후 cueTiming/`audioDurationSec` 동기화에 활용 가능한지 검토.

### 6.2 AI 서버 붙은 뒤 핵심 3가지
1. **`POST /api/voices/clone`** — 녹음 파일 전송 → `reference.*` 저장 → AI 클론 → `sample.wav` 저장 → `status=ready` / `sampleAudioUrl` 채워짐.
2. **`POST /api/tts/scene`** — scene items → AI TTS 요청 → `audioId`별 `audioUrl` 반환 → `TTSAudio` 저장(부분 실패 시 해당 item만 `error`).
3. **재생 UI(`/voice` 미리듣기 / TTS 재생)** — `sampleAudioUrl` / `audioUrl`이 실제로 재생되는지.

### 6.3 preset 나레이터(4개) 확인
- preset voiceId는 `referenceAudioUrl/referenceText`가 **null**일 수 있다 → AI 서버가 그 preset voiceId의 기본 speaker/prompt를 **자체 보유**해야 정상 합성된다(§0).


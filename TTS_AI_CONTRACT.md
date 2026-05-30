# TTS 백엔드 ↔ AI/TTS 파트 요청·응답 계약

백엔드가 AI/TTS 파트에 **① 보이스 클로닝**과 **② 음성 합성**을 요청할 때의 **JSON 계약**이다.
(현재 백엔드는 mock 단계라 실제 AI 호출은 아직 코드에 없지만, 백엔드의 `Voice`/`TTSAudio` 모델에서 그대로 도출되는 계약이다.
AI 파트는 이 형식을 받아 구현하면 되고, 실제 연동 시 백엔드 mock 부분만 이 호출로 교체한다.)

> 역할 분리
> - **Story Parse**: 감정(emotion) 결정
> - **백엔드**: ① 보이스 자산(`voiceId`) 발급 + 캐릭터에 연결, ② scene.items → 합성 대상(audio target) 구성, AI에 요청, 결과(`audioUrl`) 저장
> - **AI/TTS(김도연)**: ① 보이스 클로닝(`voiceId`에 실제 목소리 매핑 = `provider`/`model`/`sampleAudioUrl`/`status` 채우기), ② `text`를 emotion·voice로 합성해 `audioUrl` 반환  ← **이 두 가지가 AI 영역**

> **voiceId가 흐르는 길**
> `POST /api/voices`(보이스 자산 생성, voiceId 발급) → 연결 → `POST /api/tts/scene`(audio에 voiceId 복사) → AI는 그 voiceId의 목소리로 합성.
> - **dialogue**: `PATCH /api/characters/{id}/voice`로 캐릭터에 연결 → TTS가 speaker로 캐릭터 찾아 그 `voiceId` 복사.
> - **narration**: `PATCH /api/stories/{id}/narrator-voice`로 스토리에 연결(`voiceType="narrator"` 보이스만 허용 → 현재는 preset 4개) → TTS가 story의 `narratorVoiceId` 복사.

---

## 1. 보이스(Voice) 자산 — 클로닝 영역 (AI 역할 ①)

보이스는 캐릭터/배경처럼 **재사용 가능한 라이브러리 자산**이다. 백엔드가 `voiceId`를 발급하고, 실제 목소리(클로닝/모델)는 AI/TTS 파트가 그 `voiceId`에 매핑·관리한다.

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
      "voiceType": "narrator",
      "characterId": null,
      "voiceId": "voice_preset_narrator_calm_001"
    },
    {
      "audioId": "audio_mock_002",
      "itemIndex": 1,
      "type": "dialogue",
      "speaker": "어린왕자",
      "text": "싫어",
      "emotion": "angry",
      "emotionLabel": "화남",
      "voiceType": "character",
      "characterId": "char_mock_001",
      "voiceId": "voice_mock_001"
    }
  ]
}
```

### 필드 의미
| 필드 | 설명 |
|---|---|
| `audioId` | **상관관계 키.** 응답에 그대로 돌려줘야 백엔드가 매칭한다. |
| `text` | **합성할 문장.** 이걸 음성으로 만든다. |
| `emotion` | **감정 스타일 키(영문).** 음성 스타일에 적용. (`emotionLabel`은 표시용이라 무시 가능) |
| `voiceType` | `narrator`(내레이션) / `character`(대사) — 기본 목소리 갈래 |
| `voiceId` | **§1의 보이스 자산 ID.** 없으면 null → AI는 `voiceType` 기준 기본 목소리 사용. 출처: **dialogue = 매칭 캐릭터의 `voiceId`**, **narration = story의 `narratorVoiceId`** |
| `speaker` | 대사의 화자명 (narration이면 null) |
| `characterId` | dialogue의 `speaker`로 **매칭된 저장 캐릭터 ID**. narration이거나 매칭 캐릭터가 없으면 null. (매칭 키 = speaker 이름 == 캐릭터 name) |
| `itemIndex` | 원본 scene.items 인덱스 (참고용, 재번호 안 함) |

### enum 값
- `emotion`: `neutral · calm · happy · sad · angry · scared · excited · friendly · serious`
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
- **TTS**: `POST /api/tts/scene`은 위 AI 호출 없이 **mock**으로 `audioUrl=null`을 만든다. dialogue speaker→캐릭터(name 매칭)→characterId/voiceId 복사는 **이미 동작**한다(목소리 참조까지 흐름, 합성만 AI).
- 실제 연동 시 `backend/app/services/tts_service.py` / `tts_job_runner.py`의 mock 생성 부분을 위 AI 요청/응답으로 교체하고, 응답의 `audioUrl`을 `TTSAudio`에 저장하면 된다.
- 백엔드 TTS/Voice 구조·필드 상세는 `backend/README.md`의 "TTS(음성 생성) API" / "보이스(Voice) 라이브러리" 참고.

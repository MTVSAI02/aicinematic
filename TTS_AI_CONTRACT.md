# TTS 백엔드 ↔ AI/TTS 파트 요청·응답 계약

백엔드가 AI/TTS 파트에 음성 합성을 요청할 때의 **JSON 계약**이다.
(현재 백엔드는 mock 단계라 이 호출은 아직 코드에 없지만, 백엔드의 `TTSAudio` 모델에서 그대로 도출되는 계약이다.
AI 파트는 이 형식을 받아 구현하면 되고, 실제 연동 시 백엔드 mock 부분만 이 호출로 교체한다.)

> 역할 분리
> - **Story Parse**: 감정(emotion) 결정
> - **백엔드 TTS**: scene.items → 합성 대상(audio target) 구성, AI에 요청, 결과(`audioUrl`) 저장
> - **AI/TTS**: text를 emotion/voice로 합성해 `audioUrl` 반환  ← 이 문서가 정의하는 부분

---

## 1. 백엔드 → AI/TTS 요청 (scene 단위, 배치)

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
      "voiceId": null
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
      "characterId": null,
      "voiceId": null
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
| `voiceId` | **현재 항상 null** → AI는 `voiceType` 기준 기본 목소리 사용. 추후 캐릭터별 목소리 ID가 들어옴. |
| `speaker` | 대사의 화자명 (narration이면 null) |
| `characterId` | 캐릭터 식별 (현재 null, 추후 매핑) |
| `itemIndex` | 원본 scene.items 인덱스 (참고용) |

### enum 값
- `emotion`: `neutral · calm · happy · sad · angry · scared · excited · friendly · serious`
- `voiceType`: `narrator · character`

---

## 2. AI/TTS → 백엔드 응답

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

## 3. 동기 / 비동기

AI 파트가 자유롭게 선택한다.

- **동기**: 위 응답을 바로 반환.
- **비동기**: `jobId`를 먼저 주고 콜백/폴링으로 위 `audios` 형태를 전달.

백엔드는 받은 `audioUrl`을 해당 `audioId`의 `TTSAudio.audioUrl`에 채우기만 하면 된다.

---

## 4. 핵심 요약 (3줄)
1. 백엔드가 **scene 단위로 `items` 배열**(text + emotion + voiceType + audioId)을 보낸다.
2. AI는 각 item을 합성해 **`audioId`마다 `audioUrl`을 돌려준다**.
3. **감정 = `emotion`(영문 키, 문장별), 목소리 = `voiceType`(추후 `voiceId`, 캐릭터 고정).**

---

## 참고: 현재 백엔드 상태
- 현재 `POST /api/tts/scene`은 위 AI 호출 없이 **mock**으로 `audioUrl=null`을 만든다.
- 실제 연동 시 `backend/app/services/tts_service.py` / `job_manager.py`의 mock 생성 부분을 위 AI 요청/응답으로 교체하고, 응답의 `audioUrl`을 `TTSAudio`에 저장하면 된다.
- 백엔드 TTS 구조/필드 상세는 `backend/README.md`의 "TTS(음성 생성) API" 참고.

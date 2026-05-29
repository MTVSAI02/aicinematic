# Voice Profile Contract

이 문서는 프론트 `ExportPage`의 보이스 클로닝 UI가 기대하는 캐릭터 목소리 데이터와 API 계약 초안이다.

## VoiceProfile

```ts
type VoiceProfile = {
  id: string | null;
  character_id: string | null;
  mode: 'preset' | 'clone';
  label: string;
  speaker: string | null;
  reference_audio_url: string | null;
  reference_text: string | null;
  sample_audio_url: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};
```

## Character에 연결되는 형태

```ts
type Character = {
  id: string;
  name: string;
  tags: string;
  image_url: string | null;
  locked: boolean;
  voice_profile: VoiceProfile | null;
};
```

## 기본 TTS

```http
POST /voice/tts
Content-Type: application/json
```

### Request

```json
{
  "story_id": "story_001",
  "scene_id": "scene_001"
}
```

### Response

```json
{
  "scene_id": "scene_001",
  "audio_url": "/storage/audio/story_001/scene_001.wav",
  "audio_duration_sec": 4.3,
  "voice_type": "narrator"
}
```

## 보이스 클로닝 샘플 업로드

```http
POST /voice/clone/upload
Content-Type: multipart/form-data
```

### Form Data

```text
character_id=char_luna
reference_text=안녕, 나는 달빛 숲의 루나야.
audio_file=<wav|mp3|m4a>
```

### Response

```json
{
  "character_id": "char_luna",
  "voice_profile": {
    "id": "voice_char_luna_clone",
    "character_id": "char_luna",
    "mode": "clone",
    "label": "루나 클론 목소리",
    "speaker": null,
    "reference_audio_url": "/storage/voices/char_luna/reference.wav",
    "reference_text": "안녕, 나는 달빛 숲의 루나야.",
    "sample_audio_url": null,
    "created_at": "2026-05-29T00:00:00.000Z",
    "updated_at": "2026-05-29T00:00:00.000Z"
  }
}
```

## 클론 음성 테스트 합성

```http
POST /voice/clone/generate
Content-Type: application/json
```

### Request

```json
{
  "character_id": "char_luna",
  "text": "달빛 숲으로 가 보자!"
}
```

### Response

```json
{
  "character_id": "char_luna",
  "audio_url": "/storage/voices/char_luna/test.wav",
  "audio_duration_sec": 4.3
}
```

## 프론트 연결 위치

- `frontend/src/api/voiceApi.js`
  - `generateSceneVoice`
  - `uploadVoiceSample`
  - `generateClonedVoice`
- `frontend/src/store/useCharacterStore.js`
  - `setCharacterVoiceProfile`
- `frontend/src/pages/export/VoiceClonePanel.jsx`

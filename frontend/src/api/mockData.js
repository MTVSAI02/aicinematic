export const mockCharacters = [
  {
    id: 'char_luna',
    name: '루나',
    voiceMode: 'preset',
    voiceLabel: '따뜻한 여자아이 목소리',
    voice_profile: {
      id: 'voice_char_luna',
      character_id: 'char_luna',
      mode: 'preset',
      label: '따뜻한 여자아이 목소리',
      speaker: 'Sohee',
      reference_audio_url: null,
      reference_text: null,
      sample_audio_url: null,
      created_at: null,
      updated_at: null,
    },
  },
]

export const mockScenes = [
  {
    id: 'scene_001',
    order: 1,
    type: 'narration',
    speaker: null,
    line: '옛날 옛날, 달빛 숲에 작은 별이 살았습니다.',
    durationSec: 5.0,
    audioPath: null,
    audioDurationSec: null,
  },
  {
    id: 'scene_002',
    order: 2,
    type: 'dialogue',
    speaker: 'char_luna',
    line: '나는 별을 찾으러 갈 거야!',
    durationSec: 4.0,
    audioPath: null,
    audioDurationSec: null,
  },
  {
    id: 'scene_003',
    order: 3,
    type: 'dialogue',
    speaker: 'char_luna',
    line: '저기 반짝이는 문이 보여!',
    durationSec: 4.5,
    audioPath: null,
    audioDurationSec: null,
  },
]

export const mockStoreScenes = mockScenes.map((scene) => ({
  id: scene.id,
  order: scene.order,
  duration: scene.durationSec,
  segments: [
    {
      type: scene.type,
      speaker: scene.speaker,
      text: scene.line,
    },
  ],
  background_tag: null,
  character_id: scene.speaker,
  image_url: null,
  audio_url: scene.audioPath,
  audio_duration_sec: scene.audioDurationSec,
}))

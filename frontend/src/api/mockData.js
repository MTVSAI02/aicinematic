export const mockCharacters = [
  {
    id: 'char_luna',
    name: '루나',
    voiceMode: 'preset',
    voiceLabel: '따뜻한 여자아이 목소리',
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

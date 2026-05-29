const MOCK_AUDIO_DURATION_SEC = 4.3
const SAMPLE_RATE = 8000

function writeAscii(view, offset, text) {
  for (let i = 0; i < text.length; i += 1) {
    view.setUint8(offset + i, text.charCodeAt(i))
  }
}

function createMockWavDataUrl(durationSec = MOCK_AUDIO_DURATION_SEC) {
  const sampleCount = Math.floor(SAMPLE_RATE * durationSec)
  const dataSize = sampleCount * 2
  const buffer = new ArrayBuffer(44 + dataSize)
  const view = new DataView(buffer)

  writeAscii(view, 0, 'RIFF')
  view.setUint32(4, 36 + dataSize, true)
  writeAscii(view, 8, 'WAVE')
  writeAscii(view, 12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, SAMPLE_RATE, true)
  view.setUint32(28, SAMPLE_RATE * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeAscii(view, 36, 'data')
  view.setUint32(40, dataSize, true)

  for (let i = 0; i < sampleCount; i += 1) {
    const fadeIn = Math.min(i / (SAMPLE_RATE * 0.05), 1)
    const fadeOut = Math.min((sampleCount - i) / (SAMPLE_RATE * 0.08), 1)
    const envelope = Math.min(fadeIn, fadeOut)
    const tone = Math.sin((2 * Math.PI * 440 * i) / SAMPLE_RATE)
    const sample = Math.round(tone * envelope * 0.18 * 32767)
    view.setInt16(44 + i * 2, sample, true)
  }

  let binary = ''
  const bytes = new Uint8Array(buffer)
  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i])
  }

  return `data:audio/wav;base64,${btoa(binary)}`
}

export async function generateSceneVoice({ storyId, scene }) {
  if (!storyId || !scene?.id) {
    throw new Error('storyId와 scene 정보가 필요합니다.')
  }

  await new Promise((resolve) => setTimeout(resolve, 800))

  const sceneType = scene.type ?? scene.segments?.[0]?.type ?? 'narration'

  return {
    sceneId: scene.id,
    voiceType: sceneType === 'narration' ? 'narrator' : 'character',
    audioPath: createMockWavDataUrl(),
    audioDurationSec: MOCK_AUDIO_DURATION_SEC,
  }
}

export async function uploadVoiceSample({ characterId, file, referenceText }) {
  if (!characterId) {
    throw new Error('characterId가 필요합니다.')
  }
  if (!file) {
    throw new Error('음성 샘플 파일이 필요합니다.')
  }
  if (!referenceText?.trim()) {
    throw new Error('샘플에서 말한 문장을 입력해야 합니다.')
  }

  await new Promise((resolve) => setTimeout(resolve, 900))

  return {
    characterId,
    voiceProfile: {
      id: `voice_${characterId}_clone`,
      character_id: characterId,
      mode: 'clone',
      label: '업로드 샘플 기반 클론 목소리',
      speaker: null,
      reference_audio_url: URL.createObjectURL(file),
      reference_text: referenceText.trim(),
      sample_audio_url: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  }
}

export async function generateClonedVoice({ characterId, text }) {
  if (!characterId) {
    throw new Error('characterId가 필요합니다.')
  }
  if (!text?.trim()) {
    throw new Error('테스트 문장을 입력해야 합니다.')
  }

  await new Promise((resolve) => setTimeout(resolve, 900))

  return {
    characterId,
    audioPath: createMockWavDataUrl(),
    audioDurationSec: MOCK_AUDIO_DURATION_SEC,
  }
}

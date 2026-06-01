import { jsonBody, request } from '@/utils/request'

const JOB_POLL_INTERVAL_MS = 500
const JOB_POLL_LIMIT = 20

function getSceneId(scene) {
  return scene.sceneId ?? scene.id
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function waitForJob(jobId) {
  for (let count = 0; count < JOB_POLL_LIMIT; count += 1) {
    const job = await request(`/api/jobs/${jobId}`)
    if (job.status === 'completed') return job
    if (job.status === 'failed') {
      throw new Error(job.error ?? 'TTS 생성 작업이 실패했습니다.')
    }
    await sleep(JOB_POLL_INTERVAL_MS)
  }

  throw new Error('TTS 생성 작업 시간이 초과되었습니다.')
}

export async function generateSceneVoice({ storyId, scene }) {
  const sceneId = getSceneId(scene)
  if (!storyId || !sceneId) {
    throw new Error('storyId와 scene 정보가 필요합니다.')
  }

  if (!storyId.startsWith('story_mock_')) {
    throw new Error(
      '실제 TTS는 백엔드에 저장된 스토리에서만 생성할 수 있습니다. 스토리 입력에서 씬 분해를 먼저 진행해 주세요.',
    )
  }

  const createdJob = await request('/api/tts/scene', {
    ...jsonBody({ storyId, sceneId }),
    method: 'POST',
  })
  const job = await waitForJob(createdJob.jobId)
  const audios = job.result?.audios ?? []
  const playableAudios = audios.filter((audio) => audio.audioUrl)
  const firstPlayableAudio = playableAudios[0]

  if (playableAudios.length === 0) {
    const backendErrors = audios
      .map((audio) => audio.error)
      .filter(Boolean)
      .join('\n')

    if (backendErrors) {
      throw new Error(`TTS 음성 파일 생성 실패:\n${backendErrors}`)
    }

    throw new Error(
      '백엔드가 TTS 메타만 생성했고 음성 파일 URL은 비어 있습니다. 백엔드를 QWEN_TTS_ENABLED=1로 실행했는지 확인해 주세요.',
    )
  }

  const totalAudioDurationSec = playableAudios.reduce(
    (total, audio) => total + (audio.durationSec ?? 0),
    0,
  )

  return {
    sceneId,
    voiceType: firstPlayableAudio.voiceType,
    audioPath: firstPlayableAudio.audioUrl,
    audioDurationSec:
      totalAudioDurationSec ||
      firstPlayableAudio.durationSec ||
      firstPlayableAudio.audioDurationSec ||
      scene.durationSec ||
      scene.duration ||
      3,
    audioItems: audios,
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

  throw new Error('보이스 클로닝 실제 합성 API는 아직 백엔드에 연결되지 않았습니다.')
}

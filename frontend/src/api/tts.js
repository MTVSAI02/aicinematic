import { jsonBody, request } from '@/utils/request'

const JOB_POLL_INTERVAL_MS = 1000
const JOB_POLL_LIMIT = 900

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

export async function generateSceneTts({ storyId, scene }) {
  const sceneId = getSceneId(scene)
  if (!storyId || !sceneId) {
    throw new Error('storyId와 scene 정보가 필요합니다.')
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
      '백엔드가 TTS 메타만 생성했고 음성 파일 URL은 비어 있습니다. AI_TTS_URL과 TTS 어댑터/ComfyUI 연결을 확인해 주세요.',
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

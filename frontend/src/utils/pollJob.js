import { getJob } from '@/api/jobs'

// 비동기 Job(jobId)을 일정 주기로 폴링한다.
// - completed: job(결과 포함)을 resolve
// - failed: error.detail = job.error 를 담아 reject
// - 타임아웃(maxAttempts 초과): reject
// onStatus(job): 매 조회마다 호출(pending/running 표시용).
//
// 캐릭터/배경/보이스 클로닝/렌더링 등 모든 비동기 Job에 공통으로 사용한다.
export async function pollJob(jobId, { interval = 1500, maxAttempts = 80, onStatus } = {}) {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const job = await getJob(jobId)
    if (onStatus) onStatus(job)

    if (job.status === 'completed') return job
    if (job.status === 'failed') {
      const error = new Error('Job failed')
      error.detail = job.error
      error.job = job
      throw error
    }
    // pending / running → 대기 후 재조회
    await new Promise((resolve) => setTimeout(resolve, interval))
  }
  throw new Error('Job polling timed out')
}

import { getJob } from '@/api/jobs'

// 비동기 Job(jobId)을 일정 주기로 폴링한다.
// - completed: job(결과 포함)을 resolve
// - failed: error.detail = job.error(백엔드 실제 실패 원인)를 담아 reject
// - 타임아웃(maxAttempts 초과): error.timedOut=true 로 reject (실패가 아니라 "아직 생성 중")
// - signal(AbortSignal): abort 되면 즉시 중단(컴포넌트 언마운트 시 취소용)
// onStatus(job): 매 조회마다 호출(pending/running 표시용).
//
// 기본 interval 1500ms * maxAttempts 240 ≈ 6분. ComfyUI 생성이 길 수 있어 넉넉히 둔다.
// 캐릭터/배경/보이스 클로닝/렌더링 등 모든 비동기 Job에 공통으로 사용한다.
export async function pollJob(
  jobId,
  { interval = 1500, maxAttempts = 240, onStatus, signal } = {},
) {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    if (signal?.aborted) {
      const error = new Error('Job polling aborted')
      error.aborted = true
      throw error
    }

    const job = await getJob(jobId)
    if (onStatus) onStatus(job)

    if (job.status === 'completed') return job
    if (job.status === 'failed') {
      const error = new Error('Job failed')
      error.detail = job.error // 백엔드가 남긴 실제 실패 원인
      error.job = job
      throw error
    }
    // pending / running → 대기 후 재조회
    await new Promise((resolve) => setTimeout(resolve, interval))
  }
  // 타임아웃: 백엔드 Job은 계속 진행 중일 수 있다(실패 아님).
  const error = new Error('Job polling timed out')
  error.timedOut = true
  throw error
}

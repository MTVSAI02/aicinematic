// 백엔드 Job 조회 API. 비동기 생성(캐릭터/배경/보이스 클로닝/렌더링)의 상태 폴링에 쓴다.
import { request } from '@/utils/request'

// GET /api/jobs/{jobId} — Job 상태/결과 조회
// signal(AbortSignal): 폴링 중단 시 진행 중인 fetch도 즉시 취소하기 위해 전달한다.
export function getJob(jobId, { signal } = {}) {
  return request(`/api/jobs/${jobId}`, { signal })
}

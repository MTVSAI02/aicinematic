// 백엔드 Job 조회 API. 비동기 생성(캐릭터/배경/보이스 클로닝/렌더링)의 상태 폴링에 쓴다.
import { request } from '@/utils/request'

// GET /api/jobs/{jobId} — Job 상태/결과 조회
export function getJob(jobId) {
  return request(`/api/jobs/${jobId}`)
}

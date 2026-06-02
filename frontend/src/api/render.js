// 영상 렌더링 API. (무음 mp4 — 오디오/TTS 없음)
// 공통 fetch 래퍼(utils/request.js) 사용. 비동기 Job → utils/pollJob 으로 폴링.
import { request } from '@/utils/request'

// GET /api/stories/{storyId}/render — 스토리 최신 렌더 결과. { storyId, lastRender: {renderId,videoUrl,duration,createdAt} | null }
// 새로고침 시 기존 영상 복원용(있으면 재렌더링 없이 그대로 표시).
export function getRenderStatus(storyId) {
  return request(`/api/stories/${storyId}/render`)
}

// POST /api/stories/{storyId}/render — 무음 mp4 렌더링 Job 시작. 응답: { jobId, status, message }
// 완료 결과(GET /api/jobs/{jobId} 의 result): { renderId, storyId, videoUrl, duration }
// 사용자가 [영상 생성]/[다시 생성]을 명시적으로 누를 때만 호출한다.
export function startRender(storyId) {
  return request(`/api/stories/${storyId}/render`, { method: 'POST' })
}

// 백엔드 Timeline API. (스토리보드 기반 — scene order 고정, duration + 자막 cue 타이밍 조회·저장)
// 공통 fetch 래퍼(utils/request.js) 사용. 실패 시 error.detail 보존.
import { request, jsonBody } from '@/utils/request'

// GET /api/stories/{storyId}/timeline — 스토리 원본 순서, duration, cueTimings, totalDuration, readyStatus 등
export function getTimeline(storyId) {
  return request(`/api/stories/${storyId}/timeline`)
}

// PATCH /api/stories/{storyId}/timeline — 전체 scene 목록의 재생 길이 + 자막 cue 타이밍 저장. 순서는 변경하지 않음.
// scenes: [{ sceneId, duration, cueTimings: [{ cueOrder, startSec, durationSec }] }]
export function updateTimeline(storyId, scenes) {
  return request(`/api/stories/${storyId}/timeline`, {
    ...jsonBody({ scenes }),
    method: 'PATCH',
  })
}

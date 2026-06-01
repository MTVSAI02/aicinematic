// 백엔드 Story API 호출 함수.
// 공통 fetch 래퍼는 utils/request.js 를 사용한다 (실패 시 error.detail 보존).
import { request, jsonBody } from '@/utils/request'

// POST /api/stories/parse — 대본을 씬으로 분해 후 저장
export function parseStory({ title, script }) {
  return request('/api/stories/parse', {
    ...jsonBody({ title, script }),
    method: 'POST',
  })
}

// GET /api/stories — 저장된 스토리 목록 (배경/보이스 페이지의 스토리 선택 드롭다운용)
export function getStories() {
  return request('/api/stories')
}

// GET /api/stories/{storyId} — 저장된 스토리 단건(씬 포함). 새로고침 후 scene-check 재수화용.
export function getStory(storyId) {
  return request(`/api/stories/${storyId}`)
}

// PATCH /api/stories/{storyId}/narrator-voice — 나레이션 보이스 연결/해제
// payload: { voiceId: "voice_preset_narrator_calm_001" } 또는 { voiceId: null }(해제)
export function assignNarratorVoiceToStory(storyId, payload) {
  return request(`/api/stories/${storyId}/narrator-voice`, {
    ...jsonBody(payload),
    method: 'PATCH',
  })
}

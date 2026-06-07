// 백엔드 Story API 호출 함수.
// 공통 fetch 래퍼는 utils/request.js 를 사용한다 (실패 시 error.detail 보존).
import { request, jsonBody } from '@/utils/request'

// POST /api/stories/parse — 스토리 저장.
// payload 예) structured: { title, inputMode:'structured', scenes:[{sceneOrder, items:[{emotion,emotionLabel,speaker,text}]}] }
//            raw: { title, script } (inputMode 생략 시 raw)
export function parseStory(payload) {
  return request('/api/stories/parse', {
    ...jsonBody(payload),
    method: 'POST',
  })
}

// GET /api/stories/emotions — 감정 셀렉터 옵션 [{label, value}]
export function getEmotions() {
  return request('/api/stories/emotions')
}

// GET /api/stories — 저장된 스토리 목록 (배경/보이스 페이지의 스토리 선택 드롭다운용)
export function getStories() {
  return request('/api/stories')
}

// GET /api/stories/{storyId} — 저장된 스토리 단건(씬 포함). 새로고침 후 scene-check 재수화용.
export function getStory(storyId) {
  return request(`/api/stories/${storyId}`)
}

// DELETE /api/stories/{storyId} — 스토리 + 씬/음성/영상 삭제(캐릭터·배경은 공용 보관함이라 유지)
// 응답: { deleted: true, storyId }
export function deleteStory(storyId) {
  return request(`/api/stories/${storyId}`, { method: 'DELETE' })
}

// PATCH /api/stories/{storyId}/narrator-voice — 나레이션 보이스 연결/해제
// payload: { voiceId: "voice_preset_narrator_calm_001" } 또는 { voiceId: null }(해제)
export function assignNarratorVoiceToStory(storyId, payload) {
  return request(`/api/stories/${storyId}/narrator-voice`, {
    ...jsonBody(payload),
    method: 'PATCH',
  })
}

// GET /api/stories/{storyId}/voice-locks — 대상별(나레이션/캐릭터) 잠금 상태
// 응답: { storyId, allLocked, nextStepEnabled, voiceLocks:[{targetType,targetId,displayName,imageUrl,matched,voiceId,voiceName,lockStatus,ttsStatus,reason}] }
export function getVoiceLocks(storyId) {
  return request(`/api/stories/${storyId}/voice-locks`)
}

// POST /api/stories/{storyId}/voice-locks/{targetType}/{targetId}/lock — 대상 잠금 + 그 대상 TTS 생성 시작
export function lockVoiceTarget(storyId, targetType, targetId) {
  return request(
    `/api/stories/${storyId}/voice-locks/${targetType}/${encodeURIComponent(targetId)}/lock`,
    { method: 'POST' },
  )
}

// POST /api/stories/{storyId}/voice-locks/{targetType}/{targetId}/unlock — 대상 잠금 해제(ttsStatus=stale)
export function unlockVoiceTarget(storyId, targetType, targetId) {
  return request(
    `/api/stories/${storyId}/voice-locks/${targetType}/${encodeURIComponent(targetId)}/unlock`,
    { method: 'POST' },
  )
}

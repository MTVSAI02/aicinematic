// 백엔드 Character / Job API 호출 함수.
// 프론트는 ComfyUI를 직접 호출하지 않고, 반드시 FastAPI 백엔드만 호출한다.
// 공통 fetch 래퍼는 utils/request.js 를 사용한다.
import { request, jsonBody } from '@/utils/request'

// POST /api/characters/generate — 캐릭터 생성 Job 요청
export function generateCharacter(payload) {
  return request('/api/characters/generate', {
    ...jsonBody(payload),
    method: 'POST',
  })
}

// GET /api/jobs/{jobId} — Job 상태 조회
export function getJob(jobId) {
  return request(`/api/jobs/${jobId}`)
}

// GET /api/characters — 캐릭터 목록 조회
export function getCharacters() {
  return request('/api/characters')
}

// POST /api/characters — 이미 생성된 캐릭터 결과 직접 저장 (현재 UI 미노출, 함수만 제공)
export function createCharacter(payload) {
  return request('/api/characters', {
    ...jsonBody(payload),
    method: 'POST',
  })
}

// GET /api/characters/{characterId} — 캐릭터 단건 조회
export function getCharacter(characterId) {
  return request(`/api/characters/${characterId}`)
}

// PATCH /api/characters/{characterId} — 캐릭터 부분 수정 (name / appearancePrompt / imageUrl)
export function updateCharacter(characterId, payload) {
  return request(`/api/characters/${characterId}`, {
    ...jsonBody(payload),
    method: 'PATCH',
  })
}

// DELETE /api/characters/{characterId} — 캐릭터 삭제
export function deleteCharacter(characterId) {
  return request(`/api/characters/${characterId}`, { method: 'DELETE' })
}

// PATCH /api/characters/{characterId}/voice — 캐릭터에 보이스 연결/해제
// payload: { voiceId: "voice_mock_001" } 또는 { voiceId: null }(해제)
export function assignVoiceToCharacter(characterId, payload) {
  return request(`/api/characters/${characterId}/voice`, {
    ...jsonBody(payload),
    method: 'PATCH',
  })
}

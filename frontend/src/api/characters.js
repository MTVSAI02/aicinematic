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

// (Job 조회는 api/jobs.js 의 getJob 사용 — 캐릭터/배경/보이스 공통)

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

// PATCH /api/scenes/{sceneId}/character — 씬에 캐릭터 연결/배치 (배경 연결과 동일 패턴)
// payload: { storyId, characterId, sceneAppearancePrompt?, layout? }
//   sceneAppearancePrompt / layout 은 전달된 것만 갱신된다(부분 갱신).
//   layout: 합성 미리보기 배치 { x, y, scale, zIndex, flipX } (정규화 0~1).
//   드래그/리사이즈 저장 시엔 { storyId, characterId, layout } 만 보낸다(prompt 안 건드림).
export function assignCharacterToScene(sceneId, { storyId, characterId, sceneAppearancePrompt, layout }) {
  return request(`/api/scenes/${sceneId}/character`, {
    ...jsonBody({ storyId, characterId, sceneAppearancePrompt, layout }),
    method: 'PATCH',
  })
}

// DELETE /api/scenes/{sceneId}/character/{characterId} — 씬에서 캐릭터 1명 제거 (storyId는 쿼리)
export function removeCharacterFromScene(sceneId, characterId, storyId) {
  return request(
    `/api/scenes/${sceneId}/character/${characterId}?storyId=${encodeURIComponent(storyId)}`,
    { method: 'DELETE' },
  )
}

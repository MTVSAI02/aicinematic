// 백엔드 Background / Scene Background API 호출 함수.
// 프론트는 ComfyUI를 직접 호출하지 않고, 반드시 FastAPI 백엔드만 호출한다.
// 공통 fetch 래퍼는 utils/request.js 를 사용한다.
import { request, jsonBody } from '@/utils/request'

// POST /api/backgrounds/prompt-suggestions — 씬 기반 배경 프롬프트 추천
export function suggestBackgroundPrompt({ storyId, sceneId }) {
  return request('/api/backgrounds/prompt-suggestions', {
    ...jsonBody({ storyId, sceneId }),
    method: 'POST',
  })
}

// POST /api/backgrounds/generate — 배경 생성 Job
// 제목(name, 필수) + prompt 를 보낸다. finalPrompt 조립·negativePrompt는 백엔드/AI 서버가 담당.
// 1장 생성 → 라이브러리 자동 저장(name=제목). Job 완료 시 result.background 가 저장된 배경.
export function generateBackground({ name, prompt }) {
  return request('/api/backgrounds/generate', {
    ...jsonBody({ name, prompt }),
    method: 'POST',
  })
}

// (Job 조회는 api/jobs.js 의 getJob 사용 — 캐릭터/배경 공통)

// GET /api/backgrounds — 저장된 배경 목록
export function getBackgrounds() {
  return request('/api/backgrounds')
}

// GET /api/backgrounds/{backgroundId} — 저장된 배경 단건 (현재 UI 미사용, 함수만 제공)
export function getBackground(backgroundId) {
  return request(`/api/backgrounds/${backgroundId}`)
}

// PATCH /api/backgrounds/{backgroundId} — 배경 수정 (MVP: name 만)
export function updateBackground(backgroundId, payload) {
  return request(`/api/backgrounds/${backgroundId}`, {
    ...jsonBody(payload),
    method: 'PATCH',
  })
}

// DELETE /api/backgrounds/{backgroundId} — 배경 삭제
export function deleteBackground(backgroundId) {
  return request(`/api/backgrounds/${backgroundId}`, { method: 'DELETE' })
}

// PATCH /api/scenes/{sceneId}/background — 씬에 저장된 배경 연결 (storyId 는 body)
// 주의: candidateId 가 아니라 저장된 backgroundId 만 연결한다.
export function assignBackgroundToScene(sceneId, { storyId, backgroundId }) {
  return request(`/api/scenes/${sceneId}/background`, {
    ...jsonBody({ storyId, backgroundId }),
    method: 'PATCH',
  })
}

// 백엔드 Background / Scene Background API 호출 함수.
// 프론트는 ComfyUI를 직접 호출하지 않고, 반드시 FastAPI 백엔드만 호출한다.
// 백엔드 주소는 .env 의 VITE_API_BASE_URL 값을 사용한다 (characters.js 와 동일).
const BASE_URL = import.meta.env.VITE_API_BASE_URL

async function request(path, options) {
  const res = await fetch(`${BASE_URL}${path}`, options)

  let data = null
  try {
    data = await res.json()
  } catch {
    // 응답 본문이 JSON이 아니면 data는 null 유지
  }

  if (!res.ok) {
    const error = new Error(`HTTP ${res.status}`)
    error.status = res.status
    error.detail = data?.detail
    throw error
  }

  return data
}

function jsonBody(payload) {
  return {
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }
}

// POST /api/backgrounds/prompt-suggestions — 씬 기반 배경 프롬프트 추천
export function suggestBackgroundPrompt({ storyId, sceneId }) {
  return request('/api/backgrounds/prompt-suggestions', {
    ...jsonBody({ storyId, sceneId }),
    method: 'POST',
  })
}

// POST /api/backgrounds/generate — 배경 후보 생성 Job
// 주의: finalPrompt 가 아니라 사용자가 수정한 promptInput 만 보낸다. count 는 보내지 않는다.
export function generateBackground({ prompt, negativePrompt }) {
  return request('/api/backgrounds/generate', {
    ...jsonBody({ prompt, negativePrompt }),
    method: 'POST',
  })
}

// GET /api/jobs/{jobId} — Job 상태 조회
export function getJob(jobId) {
  return request(`/api/jobs/${jobId}`)
}

// POST /api/backgrounds — 후보 1장을 배경 라이브러리에 저장
export function saveBackground({ candidateId, name }) {
  return request('/api/backgrounds', {
    ...jsonBody({ candidateId, name }),
    method: 'POST',
  })
}

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

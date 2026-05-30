// 백엔드 Character / Job API 호출 함수.
// 프론트는 ComfyUI를 직접 호출하지 않고, 반드시 FastAPI 백엔드만 호출한다.
// 백엔드 주소는 .env 의 VITE_API_BASE_URL 값을 사용한다 (health.js / stories.js 와 동일).
const BASE_URL = import.meta.env.VITE_API_BASE_URL

// 공통 fetch 래퍼. 실패 시 백엔드 detail 을 담은 에러를 throw 한다.
async function request(path, options) {
  const res = await fetch(`${BASE_URL}${path}`, options)

  let data = null
  try {
    data = await res.json()
  } catch {
    data = null
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
    method: undefined, // caller가 지정
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }
}

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

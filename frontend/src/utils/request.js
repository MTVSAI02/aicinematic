// 백엔드(FastAPI) 호출 공통 fetch 래퍼.
// 프론트는 ComfyUI/AI 서버를 직접 호출하지 않고, 반드시 이 BASE_URL(백엔드)만 호출한다.
// 실패 시 백엔드의 detail 을 error.detail 에 담아 throw → utils/apiError.js 가 사용자 문구로 변환.
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export async function request(path, options) {
  const res = await fetch(`${BASE_URL}${path}`, options)

  let data = null
  try {
    data = await res.json()
  } catch {
    // 응답 본문이 없거나 JSON 이 아니면 data 는 null 로 둔다
  }

  if (!res.ok) {
    const error = new Error(`HTTP ${res.status}`)
    error.status = res.status
    error.detail = data?.detail
    throw error
  }

  return data
}

// JSON 본문 옵션 헬퍼. method 는 호출부에서 지정한다.
export function jsonBody(payload) {
  return {
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }
}

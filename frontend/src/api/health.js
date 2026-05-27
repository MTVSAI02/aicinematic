// 백엔드 연동 확인용 API 함수.
// 백엔드 주소는 .env 의 VITE_API_BASE_URL 값을 사용한다.
const BASE_URL = import.meta.env.VITE_API_BASE_URL

export async function checkHealth() {
  const res = await fetch(`${BASE_URL}/api/health`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

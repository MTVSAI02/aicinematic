const BASE_URL = import.meta.env.VITE_API_BASE_URL

export async function parseStory({ title, script }) {
  const res = await fetch(`${BASE_URL}/api/stories/parse`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, script }),
  })

  if (!res.ok) {
    throw new Error(`스토리 파싱 실패: HTTP ${res.status}`)
  }

  return res.json()
}

// GET /api/stories — 저장된 스토리 목록 (배경 페이지의 스토리/씬 선택 드롭다운용)
export async function getStories() {
  const res = await fetch(`${BASE_URL}/api/stories`)
  if (!res.ok) {
    throw new Error(`스토리 목록 조회 실패: HTTP ${res.status}`)
  }
  return res.json()
}

// ⚠️ 임시: AI(ComfyUI) 연결 테스트용. 실제 연동 시 삭제/교체.
//    제거 체크리스트: 루트의 TEMP_AI_CONNECTION_TEST.md 참고.
// AI 연동 상태 확인용 API.
// 프론트는 ComfyUI를 직접 호출하지 않고, 백엔드를 통해서만 AI 상태를 확인한다.
// (프론트 → 백엔드 → AI client → ComfyUI 읽기전용)
const BASE_URL = import.meta.env.VITE_API_BASE_URL

// GET /api/ai/comfy-health — ComfyUI 연결 확인 (이미지 생성 아님, 읽기전용)
export async function getComfyHealth() {
  const res = await fetch(`${BASE_URL}/api/ai/comfy-health`)
  if (!res.ok) {
    const error = new Error(`HTTP ${res.status}`)
    error.status = res.status
    throw error
  }
  return res.json()
}

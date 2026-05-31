// ⚠️ 임시: AI(ComfyUI) 연결 테스트용. 실제 연동 시 삭제/교체.
//    제거 체크리스트: 루트의 TEMP_AI_CONNECTION_TEST.md 참고.
// AI 연동 상태 확인용 API.
// 프론트는 ComfyUI를 직접 호출하지 않고, 백엔드를 통해서만 AI 상태를 확인한다.
// (프론트 → 백엔드 → AI client → ComfyUI 읽기전용)
import { request } from '@/utils/request'

// GET /api/ai/comfy-health — ComfyUI 연결 확인 (이미지 생성 아님, 읽기전용)
export function getComfyHealth() {
  return request('/api/ai/comfy-health')
}

// GET /api/ai/background-comfy-health — 배경 전용 경로 연결 확인 (읽기전용)
// 프론트 → 백엔드 → ai.image.background → ComfyUI(COMFYUI_GPU1_URL) 읽기전용
export function getBackgroundComfyHealth() {
  return request('/api/ai/background-comfy-health')
}

// GET /api/ai/voice-comfy-health — 보이스(TTS) 전용 경로 연결 확인 (읽기전용)
// 프론트 → 백엔드 → ai.voice.voice → ComfyUI(COMFYUI_VOICE_URL) 읽기전용
export function getVoiceComfyHealth() {
  return request('/api/ai/voice-comfy-health')
}

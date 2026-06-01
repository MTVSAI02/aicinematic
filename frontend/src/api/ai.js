// ⚠️ 임시: 보이스(TTS) AI 연결 테스트용. 실제 연동 시 삭제/교체.
//    캐릭터/배경은 외부 AI 서버 방식으로 전환되어 해당 health 호출은 제거했다.
//    제거 체크리스트: 루트의 TEMP_AI_CONNECTION_TEST.md 참고.
// 프론트는 ComfyUI를 직접 호출하지 않고, 백엔드를 통해서만 AI 상태를 확인한다.
import { request } from '@/utils/request'

// GET /api/ai/voice-comfy-health — 보이스(TTS) 전용 경로 연결 확인 (읽기전용)
// 프론트 → 백엔드 → ai.voice.voice → ComfyUI(COMFYUI_VOICE_URL) 읽기전용
export function getVoiceComfyHealth() {
  return request('/api/ai/voice-comfy-health')
}

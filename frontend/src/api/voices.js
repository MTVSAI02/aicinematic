// 백엔드 Voice Library API 호출 함수.
// 프론트는 AI/TTS 서버를 직접 호출하지 않고, 반드시 FastAPI 백엔드만 호출한다.
// 공통 fetch 래퍼는 utils/request.js 를 사용한다.
import { request, jsonBody } from '@/utils/request'

// GET /api/voices — 보이스 라이브러리 전체 (preset + 사용자 생성)
export function getVoices() {
  return request('/api/voices')
}

// POST /api/voices — 보이스 생성 (name/description/voicePrompt 만 전송, provider/model 은 보내지 않음)
export function createVoice(payload) {
  return request('/api/voices', { ...jsonBody(payload), method: 'POST' })
}

// POST /api/voices/clone — 보이스 클로닝(multipart). FormData 를 그대로 보낸다.
// ⚠️ Content-Type 을 직접 지정하지 않는다 → 브라우저가 multipart boundary 를 자동 설정.
// 응답: { jobId, voiceId, status, message }
export function cloneVoice(formData) {
  return request('/api/voices/clone', { method: 'POST', body: formData })
}

// POST /api/voices/{voiceId}/sample — preset/보이스 미리듣기 sample.wav 생성
export function generateVoiceSample(voiceId) {
  return request(`/api/voices/${voiceId}/sample`, { method: 'POST' })
}

// POST /api/voices/presets/samples — 기본 나레이션 preset 4개 샘플 일괄 생성
export function generatePresetVoiceSamples() {
  return request('/api/voices/presets/samples', { method: 'POST' })
}

// GET /api/voices/{voiceId} — 단건 조회
export function getVoice(voiceId) {
  return request(`/api/voices/${voiceId}`)
}

// PATCH /api/voices/{voiceId} — 보이스 메타 수정 (preset 은 백엔드가 400 으로 막음)
export function updateVoice(voiceId, payload) {
  return request(`/api/voices/${voiceId}`, { ...jsonBody(payload), method: 'PATCH' })
}

// DELETE /api/voices/{voiceId} — 보이스 삭제 (preset 은 백엔드가 400 으로 막음)
export function deleteVoice(voiceId) {
  return request(`/api/voices/${voiceId}`, { method: 'DELETE' })
}

// 백엔드가 서빙하는 미디어(/storage/...) 의 절대 URL 을 만든다.
//
// 이미지/오디오/영상은 백엔드(API 서버)의 /storage 프록시에서 내려오는데, DB/API 가 주는 값은
// '/storage/...' 상대경로다. 배포(Vercel) 환경에선 이 상대경로가 프론트 도메인 기준으로 해석돼
// 404 가 나므로(이미지 깨짐/오디오 재생 불가), API 베이스 URL 을 붙여 절대경로로 만든다.
//
// - 빈 값은 그대로 통과(렌더 측 조건부 처리 유지).
// - 이미 절대(http/https) 거나 blob:/data: 인 경우는 그대로 둔다(녹음 미리듣기 blob 등).
// - 그 외 '/storage/...' 같은 상대경로에만 베이스 URL 을 붙인다.
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export function mediaUrl(url) {
  if (!url) return url
  if (/^(https?:|blob:|data:)/i.test(url)) return url
  return `${BASE_URL}${url}`
}

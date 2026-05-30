// 백엔드/네트워크 에러를 사용자 친화적인 한국어 문장으로 변환한다.
// fetch 래퍼가 throw 하는 에러는 error.detail 에 백엔드의 detail 값을 담는다.
export function getApiErrorMessage(error) {
  if (!error) return '알 수 없는 오류가 발생했습니다.'

  const detail = error.detail

  if (typeof detail === 'string') {
    if (detail === 'Character not found') return '캐릭터를 찾을 수 없습니다.'
    if (detail === 'Job not found') return '생성 작업을 찾을 수 없습니다.'
    if (detail === 'No fields to update') return '수정할 내용을 입력해주세요.'
    if (detail === 'Character generation failed') return '캐릭터 생성에 실패했습니다.'
    return detail
  }

  // FastAPI validation error 는 detail 이 배열 형태로 온다.
  if (Array.isArray(detail)) {
    return '입력값을 확인해주세요.'
  }

  // 네트워크 단절 등 fetch 자체가 실패한 경우
  if (error instanceof TypeError) {
    return '서버에 연결할 수 없습니다. 백엔드가 실행 중인지 확인해주세요.'
  }

  return '요청 처리 중 오류가 발생했습니다.'
}

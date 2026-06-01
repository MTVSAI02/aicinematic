// ⚠️ 임시: AI(ComfyUI) 연결 테스트용 컴포넌트. 실제 ComfyUI 연동 시 삭제.
//    프론트 → 백엔드 → AI client → ComfyUI(읽기전용) 연결을 한 번에 확인한다.
//    제거 체크리스트: 루트 TEMP_AI_CONNECTION_TEST.md
import { useState } from 'react'
import { getApiErrorMessage } from '@/utils/apiError'
// 기존 디자인 톤을 그대로 쓰기 위해 캐릭터 페이지의 공용 스타일 모듈을 공유한다.
import styles from '@/pages/character/CharacterPage.module.css'

// check: 연결 확인 API 함수(필수), label: 버튼 문구, okText: 성공 문구
// (캐릭터/배경 정리 후 현재는 VoicePage 보이스 연결 확인에서만 사용)
export default function AiConnectionCheck({
  check,
  label = 'AI 서버 연결 확인',
  okText = 'AI 서버 연결됨 ✅',
}) {
  const [status, setStatus] = useState(null)
  const [checking, setChecking] = useState(false)

  async function handleCheck() {
    setChecking(true)
    setStatus(null)
    try {
      setStatus(await check())
    } catch (e) {
      setStatus({ ok: false, error: getApiErrorMessage(e) })
    } finally {
      setChecking(false)
    }
  }

  return (
    <div className={styles.aiCheck}>
      <button
        className={styles.btnSecondary}
        onClick={handleCheck}
        disabled={checking}
      >
        {checking ? '연결 확인 중...' : label}
      </button>
      {status && (
        <span className={status.ok ? styles.status : styles.error}>
          {/* ComfyUI 주소(baseUrl)는 프론트 화면에 노출하지 않는다. */}
          {status.ok ? okText : `연결 실패: ${status.error ?? '알 수 없음'}`}
        </span>
      )}
    </div>
  )
}

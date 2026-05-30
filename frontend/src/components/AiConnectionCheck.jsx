// ⚠️ 임시: AI(ComfyUI) 연결 테스트용 컴포넌트. 실제 ComfyUI 연동 시 삭제.
//    프론트 → 백엔드 → AI client → ComfyUI(읽기전용) 연결을 한 번에 확인한다.
//    제거 체크리스트: 루트 TEMP_AI_CONNECTION_TEST.md
import { useState } from 'react'
import { getComfyHealth } from '@/api/ai'
import { getApiErrorMessage } from '@/utils/apiError'
// 기존 디자인 톤을 그대로 쓰기 위해 캐릭터 페이지의 공용 스타일 모듈을 공유한다.
import styles from '@/pages/character/CharacterPage.module.css'

export default function AiConnectionCheck() {
  const [status, setStatus] = useState(null)
  const [checking, setChecking] = useState(false)

  async function handleCheck() {
    setChecking(true)
    setStatus(null)
    try {
      setStatus(await getComfyHealth())
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
        {checking ? 'AI 연결 확인 중...' : 'AI 서버 연결 확인'}
      </button>
      {status && (
        <span className={status.ok ? styles.status : styles.error}>
          {/* ComfyUI 주소(baseUrl)는 프론트 화면에 노출하지 않는다. */}
          {status.ok
            ? 'AI 서버 연결됨 ✅'
            : `AI 서버 연결 실패: ${status.error ?? '알 수 없음'}`}
        </span>
      )}
    </div>
  )
}

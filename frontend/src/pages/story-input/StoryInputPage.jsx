import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import styles from './StoryInputPage.module.css'

const PLACEHOLDER = `어린 왕자는 작은 별에 혼자 살았어요.
어린왕자: "오늘은 어디로 여행을 떠나볼까?"`

export default function StoryInputPage() {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function handleParse() {
    if (!text.trim()) return
    setLoading(true)
    // TODO: POST /stories → POST /stories/{id}/parse
    setTimeout(() => {
      setLoading(false)
      navigate('/scene-check')
    }, 500)
  }

  return (
    <div className={styles.page}>
      <h1>스토리 입력</h1>
      <p className={styles.guide}>
        내레이션과 대사를 입력하세요. 대사는 <code>화자: "대사"</code> 형식으로 써주세요.
      </p>
      <textarea
        className={styles.textarea}
        placeholder={PLACEHOLDER}
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={16}
      />
      <div className={styles.actions}>
        <span className={styles.count}>{text.length}자</span>
        <button
          className={styles.btn}
          onClick={handleParse}
          disabled={!text.trim() || loading}
        >
          {loading ? '분석 중...' : '씬 분해하기 →'}
        </button>
      </div>
    </div>
  )
}

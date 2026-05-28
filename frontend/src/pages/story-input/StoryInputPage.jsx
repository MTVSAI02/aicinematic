import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useStoryStore from '@/store/useStoryStore'
import styles from './StoryInputPage.module.css'

const PLACEHOLDER = `어린 왕자는 작은 별에 혼자 살았어요.
어린왕자: "오늘은 어디로 여행을 떠나볼까?"`

export default function StoryInputPage() {
  const navigate = useNavigate()
  const { storyText, setStoryText, setStoryId, setScenes } = useStoryStore()
  const [loading, setLoading] = useState(false)

  async function handleParse() {
    if (!storyText.trim()) return
    setLoading(true)
    try {
      // TODO: POST /stories → POST /stories/{id}/parse 연동
      // const { id } = await storyApi.create(storyText)
      // setStoryId(id)
      // const scenes = await storyApi.parse(id)
      // setScenes(scenes)
      navigate('/scene-check')
    } finally {
      setLoading(false)
    }
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
        value={storyText}
        onChange={(e) => setStoryText(e.target.value)}
        rows={16}
      />
      <div className={styles.actions}>
        <span className={styles.count}>{storyText.length}자</span>
        <button
          className={styles.btn}
          onClick={handleParse}
          disabled={!storyText.trim() || loading}
        >
          {loading ? '분석 중...' : '씬 분해하기 →'}
        </button>
      </div>
    </div>
  )
}

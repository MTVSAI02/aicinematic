import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useStoryStore from '@/store/useStoryStore'
import { parseStory } from '@/api/stories'
import styles from './StoryInputPage.module.css'

const PLACEHOLDER = `[잔잔함] 어린 왕자는 작은 별에 혼자 살았어요.
[신남] 어린왕자: "오늘은 어디로 여행을 떠나볼까?"`

const EMOTION_LABELS = '기본 · 잔잔함 · 기쁨 · 슬픔 · 화남 · 무서움 · 신남 · 다정함 · 진지함'

export default function StoryInputPage() {
  const navigate = useNavigate()
  const { storyText, setStoryText, storyTitle, setStoryId, setStoryTitle, setScenes } =
    useStoryStore()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const trimmedTitle = storyTitle.trim()
  const trimmedText = storyText.trim()
  const canParse = !!trimmedTitle && !!trimmedText && !loading

  async function handleParse() {
    if (!canParse) return
    setLoading(true)
    setError(null)
    try {
      const result = await parseStory({ title: trimmedTitle, script: storyText })
      setStoryId(result.storyId)
      setStoryTitle(result.title)
      setScenes(result.scenes)
      navigate('/scene-check')
    } catch {
      setError('스토리 분석에 실패했습니다. 백엔드 서버가 실행 중인지 확인해주세요.')
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

      <div className={styles.help}>
        <strong>감정 태그 (선택)</strong>
        <ul className={styles.helpList}>
          <li>줄 맨 앞에 <code>[감정]</code>을 붙이면 그 감정으로 지정돼요. 예: <code>[화남] 어린왕자: "싫어"</code></li>
          <li>태그가 없으면 문장 속 표현으로 감정을 <strong>자동 추정</strong>해요. (예: "안녕" → 다정함)</li>
          <li>지원 감정: {EMOTION_LABELS}</li>
          <li>지원하지 않는 감정이나 태그가 없으면 기본값(내레이션=잔잔함, 대사=기본)으로 처리돼요.</li>
        </ul>
      </div>

      <label className={styles.field}>
        제목
        <input
          className={styles.titleInput}
          placeholder="예: 어린 왕자"
          value={storyTitle}
          onChange={(e) => setStoryTitle(e.target.value)}
          maxLength={60}
        />
      </label>

      <textarea
        className={styles.textarea}
        placeholder={PLACEHOLDER}
        value={storyText}
        onChange={(e) => setStoryText(e.target.value)}
        rows={16}
      />
      {error && <p className={styles.error}>{error}</p>}
      <div className={styles.actions}>
        <span className={styles.count}>{storyText.length}자</span>
        <button className={styles.btn} onClick={handleParse} disabled={!canParse}>
          {loading ? '분석 중...' : '씬 분해하기 →'}
        </button>
      </div>
      {!loading && !trimmedTitle && (
        <p className={styles.guide}>제목을 입력하면 “씬 분해하기”가 활성화됩니다.</p>
      )}
    </div>
  )
}

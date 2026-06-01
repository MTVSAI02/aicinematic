import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import useStoryStore from '@/store/useStoryStore'
import { getStory } from '@/api/stories'
import { getApiErrorMessage } from '@/utils/apiError'
import styles from './SceneCheckPage.module.css'

export default function SceneCheckPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { scenes, storyId, setScenes, setStoryId, setStoryTitle } = useStoryStore()

  // 새로고침 등으로 store가 비어도 URL의 storyId(또는 store storyId)로 백엔드에서 씬을 다시 불러온다.
  const effectiveStoryId = searchParams.get('storyId') || storyId
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    // 이미 씬이 있으면(파싱 직후 등) 다시 부르지 않는다. storyId가 없으면 부를 수 없다.
    if (scenes.length > 0 || !effectiveStoryId) return
    setLoading(true)
    setError('')
    getStory(effectiveStoryId)
      .then((story) => {
        setStoryId(story.storyId)
        setStoryTitle(story.title)
        setScenes(story.scenes)
      })
      .catch((e) => setError(getApiErrorMessage(e)))
      .finally(() => setLoading(false))
  }, [effectiveStoryId, scenes.length, setScenes, setStoryId, setStoryTitle])

  if (loading) {
    return (
      <div className={styles.page}>
        <h1>씬 확인 · 수정</h1>
        <p className={styles.guide}>씬을 불러오는 중...</p>
      </div>
    )
  }

  if (scenes.length === 0) {
    return (
      <div className={styles.page}>
        <h1>씬 확인 · 수정</h1>
        <p className={styles.guide}>{error || '스토리를 먼저 입력해주세요.'}</p>
        <div className={styles.actions}>
          <button className={styles.btnSecondary} onClick={() => navigate('/story-input')}>
            스토리 입력으로 돌아가기
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <h1>씬 확인 · 수정</h1>
      <p className={styles.guide}>파싱된 씬을 확인하고 수정하세요.</p>

      <ul className={styles.list}>
        {scenes.map((scene) => (
          <li key={scene.sceneId} className={styles.card}>
            <span className={styles.order}>씬 {scene.order}</span>
            {scene.items.map((item, i) => (
              <p key={i} className={styles.seg}>
                <span className={`${styles.tag} ${styles[item.type]}`}>
                  {item.type === 'dialogue' ? item.speaker : '내레이션'}
                </span>
                {item.emotionLabel && (
                  <span className={styles.emotion}>🎭 {item.emotionLabel}</span>
                )}
                {item.text}
              </p>
            ))}
          </li>
        ))}
      </ul>

      <div className={styles.actions}>
        <button className={styles.btnSecondary} onClick={() => navigate('/story-input')}>
          ← 다시 입력
        </button>
        <button className={styles.btn} onClick={() => navigate('/character')}>
          캐릭터 설정 →
        </button>
      </div>
    </div>
  )
}

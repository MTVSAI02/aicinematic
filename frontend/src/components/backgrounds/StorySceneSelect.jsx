import { useEffect, useState } from 'react'
import useBackgroundStore from '@/store/useBackgroundStore'
import { getStories } from '@/api/stories'
import styles from '@/pages/background/BackgroundPage.module.css'

// 사용자는 storyId/sceneId 같은 내부 ID를 모르므로, GET /api/stories 로 채운
// 드롭다운에서 스토리 제목 / 씬 미리보기로 고르게 한다. ID는 내부에서만 처리.
// 선택값은 store(storyId/sceneId)에 저장되어 추천/씬연결에서 공유된다.

function scenePreview(scene) {
  const items = scene.items ?? []
  const narration = items.find((i) => i.type === 'narration')
  const text = (narration ?? items[0])?.text ?? ''
  const trimmed = text.length > 24 ? `${text.slice(0, 24)}…` : text
  return trimmed ? `${scene.order}. ${trimmed}` : `${scene.order}. (내용 없음)`
}

export default function StorySceneSelect() {
  const { storyId, sceneId, setStoryId, setSceneId } = useBackgroundStore()
  const [stories, setStories] = useState([])
  const [loadFailed, setLoadFailed] = useState(false)

  useEffect(() => {
    getStories()
      .then((list) => {
        setStories(list)
        setLoadFailed(false)
      })
      .catch(() => setLoadFailed(true)) // 실패를 "스토리 없음"으로 숨기지 않는다
  }, [])

  const selectedStory = stories.find((s) => s.storyId === storyId)
  const scenes = selectedStory?.scenes ?? []

  if (loadFailed) {
    return (
      <p className={styles.error}>
        스토리 목록을 불러오지 못했습니다. 백엔드가 실행 중인지 확인해주세요.
      </p>
    )
  }

  if (stories.length === 0) {
    return (
      <p className={styles.validation}>
        저장된 스토리가 없습니다. 먼저 “스토리 입력”에서 대본을 등록하세요.
      </p>
    )
  }

  return (
    <div className={styles.row}>
      <label className={styles.label}>
        스토리
        <select
          className={styles.input}
          value={storyId}
          onChange={(e) => {
            setStoryId(e.target.value)
            setSceneId('') // 스토리가 바뀌면 씬 선택을 초기화
          }}
        >
          <option value="">스토리 선택</option>
          {stories.map((s) => (
            <option key={s.storyId} value={s.storyId}>
              {s.title}
            </option>
          ))}
        </select>
      </label>

      <label className={styles.label}>
        씬
        <select
          className={styles.input}
          value={sceneId}
          onChange={(e) => setSceneId(e.target.value)}
          disabled={!storyId}
        >
          <option value="">씬 선택</option>
          {scenes.map((sc) => (
            <option key={sc.sceneId} value={sc.sceneId}>
              {scenePreview(sc)}
            </option>
          ))}
        </select>
      </label>
    </div>
  )
}

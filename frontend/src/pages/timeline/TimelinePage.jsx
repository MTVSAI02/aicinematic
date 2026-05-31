import { useNavigate } from 'react-router-dom'
import useStoryStore from '@/store/useStoryStore'
import styles from './TimelinePage.module.css'

// 백엔드 씬에는 duration 이 없으므로, 사용자가 조절하기 전 기본 재생 길이(초)
const DEFAULT_DURATION = 3

export default function TimelinePage() {
  const navigate = useNavigate()
  const { scenes, updateSceneDuration } = useStoryStore()
  const total = scenes.reduce((acc, s) => acc + (s.duration ?? DEFAULT_DURATION), 0)

  if (scenes.length === 0) {
    return (
      <div className={styles.page}>
        <h1>타임라인</h1>
        <p className={styles.empty}>씬이 없어요. 스토리를 먼저 입력해주세요.</p>
        <button className={styles.btn} onClick={() => navigate('/story-input')}>
          스토리 입력하러 가기
        </button>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <h1>타임라인</h1>
      <p className={styles.guide}>씬 순서와 재생 길이를 조절하세요. 총 {total.toFixed(1)}초</p>

      <div className={styles.track}>
        {scenes.map((scene) => {
          const duration = scene.duration ?? DEFAULT_DURATION
          return (
            <div key={scene.sceneId} className={styles.clip} style={{ flex: duration }}>
              <span className={styles.clipOrder}>씬 {scene.order}</span>
              <span className={styles.clipDuration}>{duration}s</span>
            </div>
          )
        })}
      </div>

      <ul className={styles.list}>
        {scenes.map((scene) => (
          <li key={scene.sceneId} className={styles.row}>
            <span className={styles.rowOrder}>씬 {scene.order}</span>
            <span className={styles.rowText}>{scene.items?.[0]?.text ?? ''}</span>
            <input
              className={styles.durationInput}
              type="number"
              min="1"
              step="0.5"
              value={scene.duration ?? DEFAULT_DURATION}
              onChange={(e) =>
                updateSceneDuration(scene.sceneId, parseFloat(e.target.value) || 1)
              }
            />
            <span className={styles.unit}>초</span>
          </li>
        ))}
      </ul>

      <div className={styles.actions}>
        <button className={styles.btnSecondary} onClick={() => navigate('/scene-editor')}>
          ← 씬 편집
        </button>
        <button className={styles.btn} onClick={() => navigate('/export')}>
          출력 →
        </button>
      </div>
    </div>
  )
}

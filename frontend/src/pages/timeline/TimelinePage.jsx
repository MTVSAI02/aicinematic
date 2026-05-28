import { useNavigate } from 'react-router-dom'
import styles from './TimelinePage.module.css'

const MOCK_SCENES = [
  { id: '1', order: 1, duration: 3.0, text: '어린 왕자는 작은 별에 혼자 살았어요.' },
  { id: '2', order: 2, duration: 4.0, text: '어린왕자: "오늘은 어디로 여행을 떠나볼까?"' },
]

export default function TimelinePage() {
  const navigate = useNavigate()
  const total = MOCK_SCENES.reduce((acc, s) => acc + s.duration, 0)

  return (
    <div className={styles.page}>
      <h1>타임라인</h1>
      <p className={styles.guide}>씬 순서와 재생 길이를 조절하세요. 총 {total}초</p>

      <div className={styles.track}>
        {MOCK_SCENES.map((scene) => (
          <div
            key={scene.id}
            className={styles.clip}
            style={{ flex: scene.duration }}
          >
            <span className={styles.clipOrder}>씬 {scene.order}</span>
            <span className={styles.clipDuration}>{scene.duration}s</span>
          </div>
        ))}
      </div>

      <ul className={styles.list}>
        {MOCK_SCENES.map((scene) => (
          <li key={scene.id} className={styles.row}>
            <span className={styles.rowOrder}>씬 {scene.order}</span>
            <span className={styles.rowText}>{scene.text}</span>
            <input
              className={styles.durationInput}
              type="number"
              min="1"
              step="0.5"
              defaultValue={scene.duration}
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

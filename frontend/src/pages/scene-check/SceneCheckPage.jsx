import { useNavigate } from 'react-router-dom'
import useStoryStore from '@/store/useStoryStore'
import styles from './SceneCheckPage.module.css'

export default function SceneCheckPage() {
  const navigate = useNavigate()
  const { scenes } = useStoryStore()

  if (scenes.length === 0) {
    return (
      <div className={styles.page}>
        <h1>씬 확인 · 수정</h1>
        <p className={styles.guide}>스토리를 먼저 입력해주세요.</p>
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

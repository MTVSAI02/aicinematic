import { useNavigate } from 'react-router-dom'
import styles from './SceneCheckPage.module.css'

// TODO: useSceneStore에서 씬 목록 가져오기
const MOCK_SCENES = [
  { id: '1', order: 1, segments: [{ type: 'narration', text: '어린 왕자는 작은 별에 혼자 살았어요.' }] },
  { id: '2', order: 2, segments: [{ type: 'dialogue', speaker: '어린왕자', text: '오늘은 어디로 여행을 떠나볼까?' }] },
]

export default function SceneCheckPage() {
  const navigate = useNavigate()

  return (
    <div className={styles.page}>
      <h1>씬 확인 · 수정</h1>
      <p className={styles.guide}>파싱된 씬을 확인하고 수정하세요.</p>

      <ul className={styles.list}>
        {MOCK_SCENES.map((scene) => (
          <li key={scene.id} className={styles.card}>
            <span className={styles.order}>씬 {scene.order}</span>
            {scene.segments.map((seg, i) => (
              <p key={i} className={styles.seg}>
                <span className={`${styles.tag} ${styles[seg.type]}`}>
                  {seg.type === 'dialogue' ? `${seg.speaker}` : '내레이션'}
                </span>
                {seg.text}
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

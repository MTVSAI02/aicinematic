import { useNavigate } from 'react-router-dom'
import styles from './SceneEditorPage.module.css'

// TODO: useSceneStore에서 씬 목록 가져오기
const MOCK_SCENES = [
  { id: '1', order: 1, text: '어린 왕자는 작은 별에 혼자 살았어요.' },
  { id: '2', order: 2, text: '어린왕자: "오늘은 어디로 여행을 떠나볼까?"' },
]

export default function SceneEditorPage() {
  const navigate = useNavigate()

  return (
    <div className={styles.page}>
      <h1>씬 편집</h1>
      <p className={styles.guide}>씬을 선택해 배경과 캐릭터를 설정하세요.</p>

      <div className={styles.layout}>
        <aside className={styles.sidebar}>
          <ul className={styles.sceneList}>
            {MOCK_SCENES.map((scene) => (
              <li key={scene.id} className={styles.sceneItem}>
                <span className={styles.sceneOrder}>씬 {scene.order}</span>
                <p className={styles.sceneText}>{scene.text}</p>
              </li>
            ))}
          </ul>
        </aside>

        <main className={styles.canvas}>
          <div className={styles.placeholder}>
            씬을 선택하면 편집 영역이 표시돼요.
          </div>
          <div className={styles.panel}>
            <div className={styles.panelItem}>
              <span className={styles.panelLabel}>배경</span>
              <button className={styles.panelBtn}>배경 생성</button>
            </div>
            <div className={styles.panelItem}>
              <span className={styles.panelLabel}>캐릭터</span>
              <button className={styles.panelBtn}>캐릭터 합성</button>
            </div>
          </div>
        </main>
      </div>

      <div className={styles.actions}>
        <button className={styles.btnSecondary} onClick={() => navigate('/character')}>
          ← 캐릭터
        </button>
        <button className={styles.btn} onClick={() => navigate('/timeline')}>
          타임라인 →
        </button>
      </div>
    </div>
  )
}

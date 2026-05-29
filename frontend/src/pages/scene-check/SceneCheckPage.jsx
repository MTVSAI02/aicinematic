import { useNavigate } from 'react-router-dom'
import useStoryStore from '@/store/useStoryStore'
import styles from './SceneCheckPage.module.css'

const MOCK_SCENES = [
  { id: '1', order: 1, duration: 3.0, segments: [{ type: 'narration', speaker: null, text: '어린 왕자는 작은 별에 혼자 살았어요.' }], background_tag: null, character_id: null, image_url: null, audio_url: null },
  { id: '2', order: 2, duration: 4.0, segments: [{ type: 'dialogue', speaker: '어린왕자', text: '오늘은 어디로 여행을 떠나볼까?' }], background_tag: null, character_id: null, image_url: null, audio_url: null },
]

export default function SceneCheckPage() {
  const navigate = useNavigate()
  const { scenes, setScenes } = useStoryStore()

  // 백엔드 연동 전: store가 비어있으면 mock 사용
  const displayScenes = scenes.length > 0 ? scenes : MOCK_SCENES

  function handleConfirm() {
    // store가 비어있으면 mock으로 채워두고 이동
    if (scenes.length === 0) setScenes(MOCK_SCENES)
    navigate('/character')
  }

  return (
    <div className={styles.page}>
      <h1>씬 확인 · 수정</h1>
      <p className={styles.guide}>파싱된 씬을 확인하고 수정하세요.</p>

      <ul className={styles.list}>
        {displayScenes.map((scene) => (
          <li key={scene.id} className={styles.card}>
            <span className={styles.order}>씬 {scene.order}</span>
            {scene.segments.map((seg, i) => (
              <p key={i} className={styles.seg}>
                <span className={`${styles.tag} ${styles[seg.type]}`}>
                  {seg.type === 'dialogue' ? seg.speaker : '내레이션'}
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
        <button className={styles.btn} onClick={handleConfirm}>
          캐릭터 설정 →
        </button>
      </div>
    </div>
  )
}

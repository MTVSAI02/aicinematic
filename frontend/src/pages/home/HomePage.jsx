import { useNavigate } from 'react-router-dom'
import styles from './HomePage.module.css'

export default function HomePage() {
  const navigate = useNavigate()

  return (
    <div className={styles.page}>
      <h1>AI Cinematic</h1>
      <p className={styles.sub}>스토리를 입력하면 동화 영상이 완성돼요.</p>
      <button className={styles.cta} onClick={() => navigate('/voice-input')}>
        새 프로젝트 시작
      </button>

      <section className={styles.section}>
        <h2>내 작업</h2>
        <p className={styles.empty}>아직 작업이 없어요.</p>
      </section>
    </div>
  )
}

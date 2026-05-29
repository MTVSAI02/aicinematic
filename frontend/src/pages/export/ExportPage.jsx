import { useState } from 'react'
import styles from './ExportPage.module.css'

export default function ExportPage() {
  const [jobId, setJobId] = useState(null)
  const [progress, setProgress] = useState(0)
  const [done, setDone] = useState(false)

  async function handleRender() {
    // TODO: POST /render → polling GET /render/{job_id}/status
    setJobId('mock-job-1')
    setProgress(0)
    setDone(false)

    let p = 0
    const interval = setInterval(() => {
      p += 20
      setProgress(p)
      if (p >= 100) {
        clearInterval(interval)
        setDone(true)
      }
    }, 600)
  }

  return (
    <div className={styles.page}>
      <h1>출력</h1>
      <p className={styles.guide}>영상을 렌더링하고 다운로드하세요.</p>

      {!jobId ? (
        <button className={styles.btn} onClick={handleRender}>
          렌더링 시작
        </button>
      ) : (
        <div className={styles.progressBox}>
          <div className={styles.bar}>
            <div className={styles.fill} style={{ width: `${progress}%` }} />
          </div>
          <p className={styles.progressText}>
            {done ? '완료!' : `렌더링 중... ${progress}%`}
          </p>
          {done && (
            <a className={styles.download} href="#" download="output.mp4">
              영상 다운로드
            </a>
          )}
        </div>
      )}
    </div>
  )
}

import { useEffect, useState } from 'react'
import { checkHealth } from './api/health'

function App() {
  const [status, setStatus] = useState('확인 중...')
  const [detail, setDetail] = useState(null)

  useEffect(() => {
    checkHealth()
      .then((data) => {
        setStatus('✅ 백엔드 연결 성공')
        setDetail(data)
      })
      .catch((err) => {
        setStatus('❌ 백엔드 연결 실패')
        setDetail({ error: err.message })
      })
  }, [])

  return (
    <div style={{ fontFamily: 'sans-serif', padding: '2rem' }}>
      <h1>AI Cinematic</h1>
      <h2>{status}</h2>
      <p>백엔드 주소: {import.meta.env.VITE_API_BASE_URL}</p>
      {detail && (
        <pre style={{ background: '#f4f4f4', padding: '1rem', borderRadius: 8 }}>
          {JSON.stringify(detail, null, 2)}
        </pre>
      )}
    </div>
  )
}

export default App

import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import styles from './VoiceInputPage.module.css'

const MIN_SECONDS = 20

const SAMPLE_TEXTS = [
  '안녕! 나는 별빛 숲에 사는 루나야. 오늘은 우리 함께 신나는 모험을 떠나볼까?',
  '옛날 옛적에, 하늘 위 구름 마을에 작은 요정이 살았어요.',
  '달빛이 내리는 밤, 토끼 한 마리가 방방 뛰어다니고 있었어요.',
  '우리 함께 별빛 여행을 떠나요. 마법 같은 이야기가 기다리고 있어요!',
]

const ROLES = [
  { id: 'mom', label: '엄마 목소리', emoji: '👩', desc: '나레이션·이야기꾼 역할에 사용돼요' },
  { id: 'child', label: '아이 목소리', emoji: '👧', desc: '동화 속 캐릭터 대사에 사용돼요' },
]

function formatTime(sec) {
  const m = String(Math.floor(sec / 60)).padStart(2, '0')
  const s = String(sec % 60).padStart(2, '0')
  return `${m}:${s}`
}

function getAudioDuration(url) {
  return new Promise((resolve) => {
    const audio = new Audio(url)
    audio.addEventListener('loadedmetadata', () => resolve(audio.duration))
    audio.addEventListener('error', () => resolve(0))
  })
}

export default function VoiceInputPage() {
  const navigate = useNavigate()
  const [role, setRole] = useState(null)
  const [sampleIndex, setSampleIndex] = useState(0)
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)  // 녹음 중 경과 초
  const [audioBlob, setAudioBlob] = useState(null)
  const [audioUrl, setAudioUrl] = useState(null)
  const [audioDuration, setAudioDuration] = useState(0)  // 완성된 오디오 길이(초)
  const [isSaving, setIsSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const timerRef = useRef(null)

  const sampleText = SAMPLE_TEXTS[sampleIndex]
  const progressPct = Math.min((recordingTime / MIN_SECONDS) * 100, 100)
  const isMinReached = recordingTime >= MIN_SECONDS
  const isDurationOk = audioDuration >= MIN_SECONDS
  const canSave = !!role && !!audioBlob && isDurationOk

  // 언마운트 시 타이머/스트림 정리
  useEffect(() => {
    return () => {
      clearInterval(timerRef.current)
      mediaRecorderRef.current?.stop()
    }
  }, [])

  async function handleStartRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        const url = URL.createObjectURL(blob)
        const duration = await getAudioDuration(url)
        setAudioBlob(blob)
        setAudioUrl(url)
        setAudioDuration(duration)
        stream.getTracks().forEach((t) => t.stop())
      }

      mediaRecorder.start()
      setIsRecording(true)
      setRecordingTime(0)
      setAudioBlob(null)
      setAudioUrl(null)
      setAudioDuration(0)
      setMessage('')
      setError('')

      // 1초마다 타이머 증가
      timerRef.current = setInterval(() => {
        setRecordingTime((t) => t + 1)
      }, 1000)
    } catch {
      setError('마이크 접근 권한이 필요합니다. 브라우저 설정에서 허용해 주세요.')
    }
  }

  function handleStopRecording() {
    clearInterval(timerRef.current)
    mediaRecorderRef.current?.stop()
    setIsRecording(false)
  }

  async function handleFileChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    const url = URL.createObjectURL(file)
    const duration = await getAudioDuration(url)
    setAudioBlob(file)
    setAudioUrl(url)
    setAudioDuration(duration)
    setMessage('')
    setError('')
  }

  function handleReset() {
    clearInterval(timerRef.current)
    setIsRecording(false)
    setRecordingTime(0)
    setAudioBlob(null)
    setAudioUrl(null)
    setAudioDuration(0)
    setMessage('')
    setError('')
  }

  async function handleSave() {
    if (!canSave) return
    setIsSaving(true)
    setMessage('')
    setError('')
    try {
      // TODO: API 연동 — uploadVoiceSample({ role, audioBlob, referenceText: sampleText })
      await new Promise((r) => setTimeout(r, 800))
      setMessage('목소리가 저장됐어요! 스토리를 만들어볼까요?')
      setTimeout(() => navigate('/story-input'), 1200)
    } catch {
      setError('저장에 실패했어요. 다시 시도해 주세요.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className={styles.page}>
      <h1>음성 입력</h1>
      <p className={styles.help}>
        동화 속 캐릭터 목소리를 직접 만들어보세요. 녹음한 목소리는 AI가 학습해
        나중에 TTS 대사 생성에 쓰여요.{' '}
        <strong>최소 20초 이상 녹음</strong>이 필요해요.
        지금 건너뛰어도 나중에 추가할 수 있어요.
      </p>

      {/* Step 1 — 역할 선택 */}
      <section className={styles.section}>
        <h2 className={styles.stepTitle}>
          <span className={styles.stepBadge}>1</span>
          누구의 목소리인가요?
        </h2>
        <div className={styles.roleGrid}>
          {ROLES.map((r) => (
            <button
              key={r.id}
              className={`${styles.roleCard} ${role === r.id ? styles.roleCardSelected : ''}`}
              onClick={() => setRole(r.id)}
            >
              <span className={styles.roleEmoji}>{r.emoji}</span>
              <span className={styles.roleLabel}>{r.label}</span>
              <span className={styles.roleDesc}>{r.desc}</span>
            </button>
          ))}
        </div>
      </section>

      {/* Step 2 — 샘플 문장 */}
      <section className={styles.section}>
        <h2 className={styles.stepTitle}>
          <span className={styles.stepBadge}>2</span>
          아래 문장을 따라 읽어주세요
        </h2>
        <div className={styles.sampleBox}>
          <p className={styles.sampleText}>{sampleText}</p>
          <button
            className={styles.refreshBtn}
            disabled={isRecording}
            onClick={() => setSampleIndex((i) => (i + 1) % SAMPLE_TEXTS.length)}
          >
            다른 문장 ↻
          </button>
        </div>
      </section>

      {/* Step 3 — 녹음 */}
      <section className={styles.section}>
        <h2 className={styles.stepTitle}>
          <span className={styles.stepBadge}>3</span>
          녹음하기
          <span className={styles.minLabel}>최소 20초</span>
        </h2>

        <div className={styles.recordArea}>
          {!audioUrl ? (
            <>
              <div className={styles.recordControls}>
                <button
                  className={`${styles.recordBtn} ${isRecording ? styles.recordBtnActive : ''}`}
                  onClick={isRecording ? handleStopRecording : handleStartRecording}
                >
                  {isRecording ? (
                    <>
                      <span className={styles.recordDot} />
                      {formatTime(recordingTime)}
                      {isMinReached ? ' — 중지' : ` — ${MIN_SECONDS - recordingTime}초 더`}
                    </>
                  ) : (
                    <>🎙 녹음 시작</>
                  )}
                </button>

                {/* 진행 바 */}
                {isRecording && (
                  <div className={styles.progressWrap}>
                    <div className={styles.progressTrack}>
                      <div
                        className={`${styles.progressBar} ${isMinReached ? styles.progressBarOk : ''}`}
                        style={{ width: `${progressPct}%` }}
                      />
                    </div>
                    <span className={`${styles.progressLabel} ${isMinReached ? styles.progressLabelOk : ''}`}>
                      {isMinReached ? '✓ 충분해요!' : `${recordingTime} / ${MIN_SECONDS}초`}
                    </span>
                  </div>
                )}
              </div>

              <span className={styles.orDivider}>또는</span>

              <label className={styles.uploadLabel}>
                <input
                  type="file"
                  accept="audio/*"
                  className={styles.fileInput}
                  onChange={handleFileChange}
                />
                📂 파일 업로드
              </label>
            </>
          ) : (
            <div className={styles.previewArea}>
              <div className={styles.previewTop}>
                <audio className={styles.audio} controls src={audioUrl} />
                <button className={styles.resetBtn} onClick={handleReset}>
                  다시 녹음
                </button>
              </div>
              {/* 길이 검증 결과 */}
              {isDurationOk ? (
                <p className={styles.durationOk}>
                  ✓ {Math.floor(audioDuration)}초 — 저장할 수 있어요
                </p>
              ) : (
                <p className={styles.durationWarn}>
                  ⚠ {Math.floor(audioDuration)}초 — 20초 이상 녹음이 필요해요. 다시 녹음해 주세요.
                </p>
              )}
            </div>
          )}
        </div>

        <p className={styles.consent}>
          본인 또는 사용 허가를 받은 목소리만 업로드해 주세요.
        </p>
      </section>

      {message && <p className={styles.message}>{message}</p>}
      {error && <p className={styles.error}>{error}</p>}

      <div className={styles.pageNav}>
        <button className={styles.btnSecondary} onClick={() => navigate('/')}>
          ← 홈
        </button>
        <div className={styles.navRight}>
          <button
            className={styles.btnSecondary}
            onClick={() => navigate('/story-input')}
          >
            나중에 하기
          </button>
          <button
            className={styles.btn}
            disabled={!canSave || isSaving}
            onClick={handleSave}
          >
            {isSaving ? '저장 중…' : '저장하고 계속 →'}
          </button>
        </div>
      </div>
    </div>
  )
}

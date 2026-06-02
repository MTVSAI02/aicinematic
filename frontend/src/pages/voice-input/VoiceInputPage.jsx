import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { cloneVoice, getVoice } from '@/api/voices'
import { pollJob } from '@/utils/pollJob'
import { getApiErrorMessage } from '@/utils/apiError'
import useVoiceStore from '@/store/useVoiceStore'
import styles from './VoiceInputPage.module.css'

const MIN_SECONDS = 20
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''
const ALLOWED_EXT = ['webm', 'wav', 'mp3', 'm4a']

// 20초 녹음 분량(각 3~4문장). 서술+대사+감탄이 섞여 억양이 다양해 클로닝 품질에 유리.
const SAMPLE_TEXTS = [
  '안녕! 나는 별빛 숲에 사는 작은 여우 루나야. 오늘은 너와 함께 반짝이는 별빛을 따라 신나는 모험을 떠나려고 해. 준비됐니? 그럼 깊게 숨을 들이쉬고, 천천히 나를 따라와 줘.',
  '옛날 옛적, 구름보다 높은 곳에 작은 마을이 있었어요. 그곳 아이들은 매일 밤 별을 세며 잠이 들었고, 아침이면 햇살을 맞으며 노래를 불렀답니다. 오늘은 그 마을의 가장 따뜻한 이야기를 들려줄게요.',
  '달빛이 조용히 내리던 밤, 토끼 한 마리가 깡총깡총 들판을 가로질러 뛰어갔어요. "기다려! 같이 가!" 멀리서 친구의 목소리가 들려왔지요. 둘은 손을 잡고 환하게 웃으며 별이 쏟아지는 언덕 위로 달려갔답니다.',
  '따뜻한 바람이 부는 봄날, 작은 새 한 마리가 처음으로 하늘을 날았어요. 무섭기도 했지만 날개를 활짝 펴자 온 세상이 발아래 펼쳐졌죠. "와, 내가 정말 날고 있어!" 새는 기쁨에 가득 차 큰 소리로 노래했답니다.',
]

// 누가 녹음했는지 (speakerLabel). voiceType(용도)과 독립.
const SPEAKERS = [
  { id: 'mom', label: '엄마', emoji: '👩' },
  { id: 'child', label: '아이', emoji: '👧' },
  { id: 'custom', label: '직접 입력', emoji: '✏️' },
]

// 이 목소리의 추천 용도(voiceType). 연결을 제한하지 않는 분류 태그일 뿐 — /voice에서 어디든 연결 가능.
const VOICE_TYPES = [
  { id: 'narrator', label: '나레이션에 추천', emoji: '📖', desc: '이야기를 읽어주는 목소리로 추천' },
  { id: 'character', label: '캐릭터에 추천', emoji: '🧒', desc: '등장인물 대사 목소리로 추천' },
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

function extOf(name) {
  return name && name.includes('.') ? name.split('.').pop().toLowerCase() : ''
}

export default function VoiceInputPage() {
  const navigate = useNavigate()
  const addVoice = useVoiceStore((s) => s.addVoice)

  // 입력
  const [speaker, setSpeaker] = useState(null) // mom | child | custom
  const [customSpeaker, setCustomSpeaker] = useState('')
  const [voiceType, setVoiceType] = useState(null) // narrator | character (추천 태그)
  const [name, setName] = useState('')
  const [voicePrompt, setVoicePrompt] = useState('')
  const [sampleIndex, setSampleIndex] = useState(0)

  // 녹음/오디오
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [audioBlob, setAudioBlob] = useState(null)
  const [audioUrl, setAudioUrl] = useState(null)
  const [audioDuration, setAudioDuration] = useState(0)

  // 흐름 상태
  const [phase, setPhase] = useState('form') // form | submitting | processing | completed | failed
  const [resultVoice, setResultVoice] = useState(null)
  const [error, setError] = useState('')

  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const timerRef = useRef(null)
  const abortRef = useRef(null)
  const objectUrlRef = useRef(null) // 미리듣기 objectURL — 교체/정리 시 revoke

  // preview용 objectURL 교체(이전 것 revoke → 메모리 누수 방지). url=null이면 정리만.
  function setPreviewUrl(url) {
    if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
    objectUrlRef.current = url
    setAudioUrl(url)
  }

  // MediaRecorder 가 녹음 중일 때만 stop (이미 inactive면 재호출 시 예외 방지)
  function stopRecorderSafely() {
    const rec = mediaRecorderRef.current
    if (rec && rec.state !== 'inactive') rec.stop()
  }

  const speakerLabel = speaker === 'custom' ? customSpeaker.trim() : SPEAKERS.find((s) => s.id === speaker)?.label || ''
  const sampleText = SAMPLE_TEXTS[sampleIndex]
  const progressPct = Math.min((recordingTime / MIN_SECONDS) * 100, 100)
  const isMinReached = recordingTime >= MIN_SECONDS
  const isDurationOk = audioDuration >= MIN_SECONDS
  const canSubmit =
    !!speakerLabel && !!voiceType && !!name.trim() && !!audioBlob && isDurationOk

  useEffect(() => {
    return () => {
      clearInterval(timerRef.current)
      stopRecorderSafely()
      abortRef.current?.abort()
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current) // preview URL 정리
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
        setPreviewUrl(url)
        setAudioDuration(duration)
        stream.getTracks().forEach((t) => t.stop())
      }
      mediaRecorder.start()
      setIsRecording(true)
      setRecordingTime(0)
      setAudioBlob(null)
      setPreviewUrl(null)
      setAudioDuration(0)
      setError('')
      timerRef.current = setInterval(() => setRecordingTime((t) => t + 1), 1000)
    } catch {
      setError('마이크 접근 권한이 필요합니다. 브라우저 설정에서 허용해 주세요.')
    }
  }

  function handleStopRecording() {
    clearInterval(timerRef.current)
    stopRecorderSafely()
    setIsRecording(false)
  }

  async function handleFileChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    if (!ALLOWED_EXT.includes(extOf(file.name))) {
      setError(`지원하지 않는 형식이에요. (${ALLOWED_EXT.join(', ')}만 가능)`)
      return
    }
    const url = URL.createObjectURL(file)
    const duration = await getAudioDuration(url)
    setAudioBlob(file)
    setPreviewUrl(url)
    setAudioDuration(duration)
    setError('')
  }

  function handleResetAudio() {
    clearInterval(timerRef.current)
    stopRecorderSafely()
    setIsRecording(false)
    setRecordingTime(0)
    setAudioBlob(null)
    setPreviewUrl(null)
    setAudioDuration(0)
    setError('')
  }

  function buildFormData() {
    const fd = new FormData()
    fd.append('name', name.trim())
    fd.append('voiceType', voiceType)
    fd.append('referenceText', sampleText) // 따라 읽은 문장 = referenceText
    if (voicePrompt.trim()) fd.append('voicePrompt', voicePrompt.trim())
    if (speakerLabel) fd.append('speakerLabel', speakerLabel)
    const file =
      audioBlob instanceof File
        ? audioBlob
        : new File([audioBlob], 'reference.webm', { type: audioBlob?.type || 'audio/webm' })
    fd.append('audioFile', file)
    return fd
  }

  async function handleSubmit() {
    if (!canSubmit) return
    setPhase('submitting')
    setError('')
    const controller = new AbortController()
    abortRef.current = controller
    try {
      const { jobId, voiceId } = await cloneVoice(buildFormData())
      setPhase('processing')
      await pollJob(jobId, { interval: 1200, signal: controller.signal })
      // 완료 → 결과 보이스 조회 후 라이브러리에도 반영
      const voice = await getVoice(voiceId)
      setResultVoice(voice)
      addVoice(voice)
      setPhase('completed')
    } catch (e) {
      if (e?.aborted) return
      const detail = e?.detail || getApiErrorMessage(e)
      setError(detail)
      setPhase('failed')
    }
  }

  function handleRetry() {
    setError('')
    setPhase('form')
  }

  function handleRecordAgain() {
    handleResetAudio()
    setResultVoice(null)
    setPhase('form')
  }

  // AI 미연결 등 백엔드 실패를 사용자에게 친절히
  const aiNotConnected = /AI_VOICE_CLONE_URL|voice clone server|보이스 클론/i.test(error || '')

  return (
    <div className={styles.page}>
      <h1>음성 입력</h1>
      <p className={styles.help}>
        먼저 목소리를 만들어 <strong>보이스 라이브러리</strong>에 저장해요. 저장한 목소리는 다음 보이스 페이지에서
        나레이션이나 캐릭터에 자유롭게 연결할 수 있습니다. <strong>최소 {MIN_SECONDS}초 이상 녹음</strong>이 정확한 분석에 좋아요.
      </p>

      {phase === 'form' && (
        <div className={styles.infoBox}>
          <span><b>1단계 (지금)</b> — 이 화면에서 목소리를 만듭니다.</span>
          <span><b>2단계 (다음)</b> — 보이스 페이지에서 만든 목소리를 나레이션 또는 캐릭터에 연결합니다.</span>
        </div>
      )}

      {/* ── 진행/결과 카드 ── */}
      {(phase === 'submitting' || phase === 'processing') && (
        <section className={styles.section}>
          <div className={styles.statusCard}>
            <div className={styles.spinner} aria-hidden="true" />
            <h2 className={styles.cardTitle}>보이스 클로닝 중입니다</h2>
            <p className={styles.cardDesc}>사용자 음성을 분석하고 샘플 목소리를 생성하고 있어요. 잠시만 기다려 주세요.</p>
          </div>
        </section>
      )}

      {phase === 'completed' && resultVoice && (
        <section className={styles.section}>
          <div className={styles.statusCard}>
            <div className={styles.emoji}>🎉</div>
            <h2 className={styles.cardTitle}>목소리가 생성되었습니다</h2>
            <p className={styles.cardDesc}>이제 보이스 페이지에서 나레이션이나 캐릭터에 연결할 수 있습니다.</p>
            <div className={styles.resultMeta}>
              <span><b>{resultVoice.name}</b></span>
              <span>{resultVoice.voiceType === 'narrator' ? '나레이션 추천' : '캐릭터 추천'}{resultVoice.speakerLabel ? ` · ${resultVoice.speakerLabel}` : ''}</span>
              <span className={styles.muted}>voiceId: {resultVoice.voiceId}</span>
            </div>
            {resultVoice.sampleAudioUrl ? (
              // eslint-disable-next-line jsx-a11y/media-has-caption
              <audio className={styles.audio} controls src={`${BASE_URL}${resultVoice.sampleAudioUrl}`} />
            ) : (
              <p className={styles.muted}>샘플 음성은 준비되는 대로 보이스 페이지에서 들을 수 있어요.</p>
            )}
            <div className={styles.cardActions}>
              <button className={styles.btn} onClick={() => navigate('/voice')}>보이스 페이지에서 연결하기</button>
              <button className={styles.btnSecondary} onClick={handleRecordAgain}>다시 녹음하기</button>
            </div>
          </div>
        </section>
      )}

      {phase === 'failed' && (
        <section className={styles.section}>
          <div className={`${styles.statusCard} ${styles.statusCardError}`}>
            <div className={styles.emoji}>⚠️</div>
            <h2 className={styles.cardTitle}>보이스 클로닝에 실패했습니다</h2>
            <p className={styles.cardDesc}>
              {aiNotConnected ? 'AI 보이스 클론 서버가 아직 연결되지 않았어요.' : error}
            </p>
            {aiNotConnected && <p className={styles.muted}>{error}</p>}
            <div className={styles.cardActions}>
              <button className={styles.btn} onClick={handleRetry}>다시 시도</button>
              <button className={styles.btnSecondary} onClick={() => navigate('/voice')}>보이스 라이브러리</button>
            </div>
          </div>
        </section>
      )}

      {/* ── 입력 폼 ── */}
      {phase === 'form' && (
        <>
          {/* 1 — 누가 녹음 */}
          <section className={styles.section}>
            <h2 className={styles.stepTitle}><span className={styles.stepBadge}>1</span>누가 녹음하나요?</h2>
            <div className={styles.roleGrid}>
              {SPEAKERS.map((s) => (
                <button
                  key={s.id}
                  className={`${styles.roleCard} ${speaker === s.id ? styles.roleCardSelected : ''}`}
                  onClick={() => setSpeaker(s.id)}
                >
                  <span className={styles.roleEmoji}>{s.emoji}</span>
                  <span className={styles.roleLabel}>{s.label}</span>
                </button>
              ))}
            </div>
            {speaker === 'custom' && (
              <input
                className={styles.input}
                placeholder="누구의 목소리인가요? (예: 아빠, 할머니)"
                value={customSpeaker}
                onChange={(e) => setCustomSpeaker(e.target.value)}
                style={{ marginTop: 10 }}
              />
            )}
            <p className={styles.muted} style={{ marginTop: 8 }}>
              녹음한 사람을 표시하기 위한 정보예요. 이 선택이 나레이션/캐릭터 용도를 정하지 않습니다 —
              엄마가 녹음해도 캐릭터에, 아이가 녹음해도 나레이션에 쓸 수 있어요.
            </p>
          </section>

          {/* 2 — 추천 용도(태그) */}
          <section className={styles.section}>
            <h2 className={styles.stepTitle}><span className={styles.stepBadge}>2</span>추천 용도를 선택해주세요</h2>
            <div className={styles.roleGrid}>
              {VOICE_TYPES.map((t) => (
                <button
                  key={t.id}
                  className={`${styles.roleCard} ${voiceType === t.id ? styles.roleCardSelected : ''}`}
                  onClick={() => setVoiceType(t.id)}
                >
                  <span className={styles.roleEmoji}>{t.emoji}</span>
                  <span className={styles.roleLabel}>{t.label}</span>
                  <span className={styles.roleDesc}>{t.desc}</span>
                </button>
              ))}
            </div>
            <p className={styles.muted} style={{ marginTop: 8 }}>
              선택한 용도는 보이스 카드의 <b>추천 태그</b>로만 쓰여요. 연결을 제한하지 않습니다 —
              나레이션 추천 목소리도 캐릭터에, 캐릭터 추천 목소리도 나레이션에 연결할 수 있어요.
            </p>
          </section>

          {/* 3 — 목소리 카드 정보 */}
          <section className={styles.section}>
            <h2 className={styles.stepTitle}><span className={styles.stepBadge}>3</span>목소리 카드 정보</h2>
            <p className={styles.muted} style={{ marginTop: -2, marginBottom: 6 }}>
              보이스 페이지에서 이 목소리를 찾기 쉽게 이름과 설명을 입력해주세요.
            </p>
            <div className={styles.field}>
              <label className={styles.label}>목소리 이름 *</label>
              <input
                className={styles.input}
                placeholder="예: 엄마 목소리 / 아이가 읽은 나레이션 / 엄마가 연기한 어린왕자 목소리"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <span className={styles.hint}>보이스 라이브러리에 표시될 이름이에요. 캐릭터 이름이 아니라, 이 목소리를 구분하는 이름입니다.</span>
            </div>
            <div className={styles.field}>
              <label className={styles.label}>원하는 목소리 느낌 (선택)</label>
              <input
                className={styles.input}
                placeholder="예: 따뜻하고 차분한 목소리 / 맑고 순수한 소년 목소리 / 밝고 또랑또랑한 목소리"
                value={voicePrompt}
                onChange={(e) => setVoicePrompt(e.target.value)}
              />
              <span className={styles.hint}>AI가 목소리를 만들 때 참고할 분위기예요. 비워두어도 생성됩니다.</span>
            </div>
          </section>

          {/* 4 — 따라 읽기 문장 (referenceText) */}
          <section className={styles.section}>
            <h2 className={styles.stepTitle}><span className={styles.stepBadge}>4</span>아래 문장을 따라 읽어주세요</h2>
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

          {/* 6 — 녹음 */}
          <section className={styles.section}>
            <h2 className={styles.stepTitle}>
              <span className={styles.stepBadge}>5</span>녹음하기
              <span className={styles.minLabel}>최소 {MIN_SECONDS}초</span>
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
                      accept="audio/webm,audio/wav,audio/mpeg,audio/mp4,.webm,.wav,.mp3,.m4a"
                      className={styles.fileInput}
                      onChange={handleFileChange}
                    />
                    📂 파일 업로드
                  </label>
                </>
              ) : (
                <div className={styles.previewArea}>
                  <div className={styles.previewTop}>
                    {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
                    <audio className={styles.audio} controls src={audioUrl} />
                    <button className={styles.resetBtn} onClick={handleResetAudio}>다시 녹음</button>
                  </div>
                  {isDurationOk ? (
                    <p className={styles.durationOk}>✓ {Math.floor(audioDuration)}초 — 제출할 수 있어요</p>
                  ) : (
                    <p className={styles.durationWarn}>⚠ {Math.floor(audioDuration)}초 — 정확한 분석을 위해 {MIN_SECONDS}초 이상 녹음해 주세요.</p>
                  )}
                </div>
              )}
            </div>
            <p className={styles.consent}>본인 또는 사용 허가를 받은 목소리만 업로드해 주세요.</p>
          </section>

          {error && <p className={styles.error}>{error}</p>}

          <div className={styles.pageNav}>
            <button className={styles.btnSecondary} onClick={() => navigate('/')}>← 홈</button>
            <div className={styles.navRight}>
              <button className={styles.btnSecondary} onClick={() => navigate('/story-input')}>나중에 하기</button>
              <button className={styles.btn} disabled={!canSubmit} onClick={handleSubmit}>
                목소리 만들기 →
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

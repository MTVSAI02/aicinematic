import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { cloneVoice, getVoice } from '@/api/voices'
import { pollJob } from '@/utils/pollJob'
import { getApiErrorMessage } from '@/utils/apiError'
import useVoiceStore from '@/store/useVoiceStore'
import styles from './VoiceInputPage.module.css'

// 디자인 자산 임포트
import voiceRabbit from '@design/assets/figma-icons/Voice_input/VoiceInput_Rabbit.svg'
import voiceAdult from '@design/assets/figma-icons/Voice_input/VoiceInput_Adult.svg'
import voiceKid from '@design/assets/figma-icons/Voice_input/VoiceInput_Kid.svg'
import voiceEdit from '@design/assets/figma-icons/Voice_input/VoiceInput_Edit.svg'
import navVoice from '@design/assets/figma-icons/Nav/nav_voice.svg'
import navCharacter from '@design/assets/figma-icons/Nav/nav_character.svg'
import navVoiceInput from '@design/assets/figma-icons/Nav/nav_voice_input.svg'
import bookBg from '@design/assets/figma-images/Book.png'
import rirurChar from '@design/assets/figma-icons/RIrur.svg'

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
  { id: 'mom', label: '어른', desc: '엄마, 아빠의 목소리를 들려주세요', icon: voiceAdult },
  { id: 'child', label: '아이', desc: '우리 아이의 목소리를 들려주세요', icon: voiceKid },
  { id: 'custom', label: '직접 입력', desc: '누구든 목소리를 입력할 수 있어요', icon: voiceEdit },
]

// 이 목소리의 추천 용도(voiceType). 연결을 제한하지 않는 분류 태그일 뿐 — /voice에서 어디든 연결 가능.
const VOICE_TYPES = [
  { id: 'narrator', label: '나레이션', desc: '이야기를 읽어주는 목소리', icon: navVoice },
  { id: 'character', label: '캐릭터', desc: '등장인물의 대사 목소리', icon: navCharacter },
]

// 책 뒤에서 빼꼼 튀어나올 RIrur 캐릭터 위치 정보 (캐릭터 얼굴이 완벽하게 식별되도록 돌출 범위와 은닉 거리를 대폭 확대한 튜닝)
const RIRUR_POSITIONS = [
  // 1. 책 왼쪽 위에서 왼쪽으로 빼꼼
  { left: '-160px', top: '22%', transform: 'translateX(200px) scale(0.1)', activeTransform: 'translateX(-100px) scale(1) rotate(-75deg)', origin: 'center right' },
  // 2. 책 왼쪽 아래에서 왼쪽으로 빼꼼
  { left: '-160px', top: '62%', transform: 'translateX(200px) scale(0.1)', activeTransform: 'translateX(-100px) scale(1) rotate(-105deg)', origin: 'center right' },
  // 3. 책 오른쪽 위에서 오른쪽으로 빼꼼
  { right: '-160px', top: '22%', transform: 'translateX(-200px) scale(0.1)', activeTransform: 'translateX(100px) scale(1) rotate(75deg)', origin: 'center left' },
  // 4. 책 오른쪽 아래에서 오른쪽으로 빼꼼
  { right: '-160px', top: '62%', transform: 'translateX(-200px) scale(0.1)', activeTransform: 'translateX(100px) scale(1) rotate(105deg)', origin: 'center left' },
  // 5. 책 아래쪽 중앙에서 아래로 빼꼼 (거꾸로 매달린 형태)
  { bottom: '-160px', left: '46%', transform: 'translateY(-200px) scale(0.1) rotate(180deg)', activeTransform: 'translateY(110px) scale(1) rotate(180deg)', origin: 'top center' },
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

  // RIrur 캐릭터 인터랙티브 상태
  const [rirurPos, setRirurPos] = useState(null)
  const [rirurVisible, setRirurVisible] = useState(false)

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

  // RIrur 캐릭터 뿅 튀어나오는 타이머 설정
  useEffect(() => {
    if (phase !== 'form') {
      setRirurVisible(false)
      setRirurPos(null)
      return
    }

    let timer
    const scheduleNextPop = () => {
      // 4초 ~ 8초 사이의 랜덤 대기 시간 후에 튀어나옴
      const delay = Math.random() * 4000 + 4000
      timer = setTimeout(() => {
        setRirurPos((prev) => {
          let next
          do {
            next = Math.floor(Math.random() * RIRUR_POSITIONS.length)
          } while (next === prev && RIRUR_POSITIONS.length > 1)
          return next
        })
        setRirurVisible(true)
      }, delay)
    }

    if (!rirurVisible) {
      scheduleNextPop()
    }

    return () => clearTimeout(timer)
  }, [rirurVisible, phase])

  function handleRirurClick() {
    setRirurVisible(false)
    // 쏙 들어가는 애니메이션(400ms) 완료 후 상태 초기화
    setTimeout(() => {
      setRirurPos(null)
    }, 400)
  }

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
      {/* ── 상단 헤더 영역 ── */}
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <div className={styles.headerSubTitle}>동화 속 캐릭터에게 생생한 목소리를 입혀주세요</div>
          <h1 className={styles.headerTitle}>동화 속<br />목소리 만들기</h1>
          <p className={styles.headerDesc}>
            누가, 어떤 목소리로 이야기할지 정하고<br />
            아래 문장을 천천히 읽어주세요.<br />
            AI가 자연스러운 목소리를 만들어 드려요
          </p>
        </div>
        <div className={styles.headerRight}>
          <img src={voiceRabbit} alt="토끼 마스코트" className={styles.headerMascot} />
        </div>
      </header>

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
              <button className={styles.btnPrimary} onClick={() => navigate('/voice')}>보이스 페이지에서 연결하기</button>
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
              <button className={styles.btnPrimary} onClick={handleRetry}>다시 시도</button>
              <button className={styles.btnSecondary} onClick={() => navigate('/voice')}>보이스 라이브러리</button>
            </div>
          </div>
        </section>
      )}

      {/* ── 입력 폼 ── */}
      {phase === 'form' && (
        <div className={styles.bookContainer}>
          <img src={bookBg} alt="책 배경" className={styles.bookBackground} />
          
          {rirurPos !== null && (
            <img
              src={rirurChar}
              alt="리룰 캐릭터"
              className={styles.rirurCharacter}
              onClick={handleRirurClick}
              style={{
                top: RIRUR_POSITIONS[rirurPos].top || 'auto',
                bottom: RIRUR_POSITIONS[rirurPos].bottom || 'auto',
                left: RIRUR_POSITIONS[rirurPos].left || 'auto',
                right: RIRUR_POSITIONS[rirurPos].right || 'auto',
                transform: rirurVisible ? RIRUR_POSITIONS[rirurPos].activeTransform : RIRUR_POSITIONS[rirurPos].transform,
                transformOrigin: RIRUR_POSITIONS[rirurPos].origin,
                opacity: rirurVisible ? 1 : 0,
              }}
            />
          )}

          <div className={styles.bookContentOverlay}>
            <div className={styles.formScrollArea}>
              {/* 1 — 누가 이야기하나요? */}
              <section className={styles.section}>
                <h2 className={styles.stepTitle}>
                  <span className={styles.stepBadge}>1</span>누가 이야기하나요?
                </h2>
                <div className={styles.speakerGrid}>
                  {SPEAKERS.map((s) => (
                    <button
                      key={s.id}
                      className={`${styles.speakerCard} ${speaker === s.id ? styles.speakerCardSelected : ''}`}
                      onClick={() => setSpeaker(s.id)}
                    >
                      <img src={s.icon} alt={s.label} className={styles.speakerIcon} />
                      <span className={styles.speakerLabel}>{s.label}</span>
                      <span className={styles.speakerDesc}>{s.desc}</span>
                    </button>
                  ))}
                </div>
                {speaker === 'custom' && (
                  <div className={styles.customInputContainer}>
                    <input
                      className={styles.input}
                      placeholder="누구의 목소리인가요? (예: 아빠, 할머니)"
                      value={customSpeaker}
                      onChange={(e) => setCustomSpeaker(e.target.value)}
                    />
                  </div>
                )}
                <p className={styles.sectionHelp}>
                  <strong>녹음한 사람</strong>을 표시하기 위한 정보예요. 엄마가 녹음해도 캐릭터에, 아이가 녹음해도 나레이션에 쓸 수 있어요.
                </p>
              </section>

              {/* 2 — 어떤 목소리인가요? */}
              <section className={styles.section}>
                <h2 className={styles.stepTitle}>
                  <span className={styles.stepBadge}>2</span>어떤 목소리인가요?
                </h2>
                <div className={styles.voiceTypeGrid}>
                  {VOICE_TYPES.map((t) => (
                    <button
                      key={t.id}
                      className={`${styles.voiceTypeCard} ${voiceType === t.id ? styles.voiceTypeCardSelected : ''}`}
                      onClick={() => setVoiceType(t.id)}
                    >
                      <img src={t.icon} alt={t.label} className={styles.voiceTypeIcon} />
                      <span className={styles.voiceTypeLabel}>{t.label}</span>
                      <span className={styles.voiceTypeDesc}>{t.desc}</span>
                    </button>
                  ))}
                </div>
                <p className={styles.sectionHelp}>
                  보이스 카드의 <strong>추천 태그</strong>로만 쓰여요. 나레이션 추천 목소리도 캐릭터에, 캐릭터 추천 목소리도 나레이션에 연결 가능해요.
                </p>
              </section>

              {/* 3 — 목소리 카드 정보 */}
              <section className={styles.section}>
                <h2 className={styles.stepTitle}>
                  <span className={styles.stepBadge}>3</span>목소리 카드 정보
                </h2>
                <p className={styles.sectionSubDesc}>보이스 페이지에서 이 목소리를 찾기 쉽게 이름과 설명을 입력해주세요</p>
                
                <div className={styles.fieldGroup}>
                  <div className={styles.field}>
                    <label className={styles.fieldLabel}>목소리 이름</label>
                    <input
                      className={styles.input}
                      placeholder="예: 엄마 목소리 / 아이가 읽은 나레이션 / 엄마가 연기한 어린왕자 목소리"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                    />
                    <span className={styles.fieldHint}>보이스 라이브러리에 표시될 이름이에요. 캐릭터 이름이 아니라, 이 목소리를 구분하는 이름입니다.</span>
                  </div>
                  
                  <div className={styles.field}>
                    <label className={styles.fieldLabel}>원하는 목소리 느낌 (선택)</label>
                    <input
                      className={styles.input}
                      placeholder="예: 따뜻하고 차분한 목소리 / 맑고 순수한 목소리 / 밝고 또랑또랑한 목소리"
                      value={voicePrompt}
                      onChange={(e) => setVoicePrompt(e.target.value)}
                    />
                    <span className={styles.fieldHint}>AI가 목소리를 만들 때 참고할 분위기예요. 비워두어도 생성됩니다.</span>
                  </div>
                </div>
              </section>

              {/* 4 — 아래 문장을 따라 읽어 주세요. */}
              <section className={styles.section}>
                <h2 className={styles.stepTitle}>
                  <span className={styles.stepBadge}>4</span>아래 문장을 따라 읽어 주세요.
                </h2>
                <div className={styles.scriptBox}>
                  <p className={styles.scriptText}>{sampleText}</p>
                  <button
                    className={styles.scriptRefreshBtn}
                    disabled={isRecording}
                    onClick={() => setSampleIndex((i) => (i + 1) % SAMPLE_TEXTS.length)}
                  >
                    다른 문장 <span className={styles.refreshIcon}>↻</span>
                  </button>
                </div>
              </section>

              {/* 5 — 녹음하기 */}
              <section className={styles.section}>
                <h2 className={styles.stepTitle}>
                  <span className={styles.stepBadge}>5</span>녹음하기
                  <span className={styles.minLabel}>최소 {MIN_SECONDS}초</span>
                </h2>

                <div className={styles.recordingContainer}>
                  <div className={styles.recordingRow}>
                    {/* 좌측 안내 말풍선 */}
                    <div className={styles.speechBubbleLeft}>
                      마이크 버튼을 눌러<br />20초 이상 녹음해 주세요.
                    </div>

                    {/* 중앙 원형 녹음 버튼 */}
                    <div className={styles.micButtonWrapper}>
                      <button
                        className={`${styles.micButton} ${isRecording ? styles.micButtonActive : ''}`}
                        onClick={isRecording ? handleStopRecording : handleStartRecording}
                      >
                        <img src={navVoiceInput} alt="마이크" className={styles.micIcon} />
                        <span className={styles.micLabel}>
                          {isRecording ? formatTime(recordingTime) : '녹음하기'}
                        </span>
                      </button>
                      {isRecording && <div className={styles.micPulseBg} />}
                    </div>

                    {/* 우측 안내 말풍선 */}
                    <div className={styles.speechBubbleRight}>
                      AI가 학습해서<br />자연스러운 대화를 만들어요
                    </div>
                  </div>

                  {/* 녹음 오디오 미리보기 영역 */}
                  {audioUrl && (
                    <div className={styles.previewArea}>
                      <div className={styles.previewTop}>
                        {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
                        <audio className={styles.audio} controls src={audioUrl} />
                        <button className={styles.previewResetBtn} onClick={handleResetAudio}>다시 녹음</button>
                      </div>
                      {isDurationOk ? (
                        <p className={styles.durationOk}>✓ {Math.floor(audioDuration)}초 — 제출할 수 있어요</p>
                      ) : (
                        <p className={styles.durationWarn}>⚠ {Math.floor(audioDuration)}초 — 정확한 분석을 위해 {MIN_SECONDS}초 이상 녹음해 주세요.</p>
                      )}
                    </div>
                  )}

                  <div className={styles.orDivider}>또는</div>

                  {/* 파일 업로드 바 */}
                  <div className={styles.fileUploadContainer}>
                    <label className={styles.fileUploadBar}>
                      <input
                        type="file"
                        accept="audio/webm,audio/wav,audio/mpeg,audio/mp4,.webm,.wav,.mp3,.m4a"
                        className={styles.fileInput}
                        onChange={handleFileChange}
                      />
                      <span className={styles.folderIcon}>📁</span> 파일 업로드
                    </label>
                  </div>

                  <p className={styles.legalNotice}>본인 또는 사용 허가를 받은 목소리만 업로드해 주세요.</p>
                </div>
              </section>

              {error && <p className={styles.error}>{error}</p>}

              {/* ── 하단 네비게이션 ── */}
              <div className={styles.pageNav}>
                <button className={styles.btnSecondary} onClick={() => navigate('/story-input')}>나중에 하기</button>
                <button className={styles.btnPrimary} disabled={!canSubmit} onClick={handleSubmit}>
                  목소리 만들기 →
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import useVoiceStore from '@/store/useVoiceStore'
import useStoryStore from '@/store/useStoryStore'
import { getVoices } from '@/api/voices'
import { getStories, getVoiceLocks } from '@/api/stories'
import { getCharacters } from '@/api/characters'
import { getApiErrorMessage } from '@/utils/apiError'
import VoiceTargetPanel from '@/components/voices/VoiceTargetPanel'
import VoiceLibrary from '@/components/voices/VoiceLibrary'
import styles from './VoicePage.module.css'

import useSwingingSignboard from '@/hooks/useSwingingSignboard'

// 디자인 에셋 임포트
import headerBg from '@design/assets/figma-icons/Base/Base_voice.png'
import characterVoiceSvg from '@design/assets/figma-icons/character/character_voice.svg'
import yarnIcon from '@design/assets/figma-icons/Nav/nav_voice.svg'

export default function VoicePage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const queryStoryId = searchParams.get('storyId') || ''
  const currentStoryId = useStoryStore((s) => s.storyId)
  const storyTitle = useStoryStore((s) => s.storyTitle)

  const story = useVoiceStore((s) => s.story)
  const setVoices = useVoiceStore((s) => s.setVoices)
  const setStory = useVoiceStore((s) => s.setStory)
  const setCharacters = useVoiceStore((s) => s.setCharacters)
  const setSelectedTarget = useVoiceStore((s) => s.setSelectedTarget)
  const setVoiceLocks = useVoiceStore((s) => s.setVoiceLocks)
  const refreshVoiceLocks = useVoiceStore((s) => s.refreshVoiceLocks)
  const voiceLocks = useVoiceStore((s) => s.voiceLocks)
  const nextStepEnabled = useVoiceStore((s) => s.nextStepEnabled)
  const message = useVoiceStore((s) => s.message)
  const error = useVoiceStore((s) => s.error)

  const { titleRef, frameHeight } = useSwingingSignboard(1140 / 1470)

  const [stories, setStories] = useState([])
  const [storyId, setStoryId] = useState(queryStoryId || currentStoryId || '')
  const [loadError, setLoadError] = useState('')

  // 진입 시 보이스/스토리 목록/캐릭터 로드
  useEffect(() => {
    getVoices()
      .then(setVoices)
      .catch((e) => setLoadError(getApiErrorMessage(e)))
    getStories()
      .then(setStories)
      .catch((e) => setLoadError(getApiErrorMessage(e)))
    getCharacters()
      .then(setCharacters)
      .catch((e) =>
        setLoadError(`캐릭터 목록을 불러오지 못했습니다. ${getApiErrorMessage(e)}`)
      )
  }, [setVoices, setCharacters])

  // storyId 선택 시 해당 스토리를 store.story 로 설정.
  useEffect(() => {
    if (!storyId) {
      setStory(null)
      setSelectedTarget(null)
      return
    }
    const found = stories.find((s) => s.storyId === storyId)
    setStory(found ?? null)
    setSelectedTarget(null)
  }, [storyId, stories, setStory, setSelectedTarget])

  // storyId 별 대상별 잠금 상태 로드 (없으면 비움)
  useEffect(() => {
    if (!storyId) {
      setVoiceLocks({ voiceLocks: [], allLocked: false, nextStepEnabled: false })
      return
    }
    getVoiceLocks(storyId)
      .then(setVoiceLocks)
      .catch(() => {})
  }, [storyId, setVoiceLocks])

  // 생성 중인 대상이 있으면 폴링 (ready/failed 되면 자동 중단)
  const anyGenerating = voiceLocks.some((l) => l.ttsStatus === 'generating')
  useEffect(() => {
    if (!storyId || !anyGenerating) return undefined
    const timer = setInterval(() => refreshVoiceLocks(), 3000)
    return () => clearInterval(timer)
  }, [storyId, anyGenerating, refreshVoiceLocks])

  function handleStoryChange(nextStoryId) {
    setStoryId(nextStoryId)
  }

  return (
    <div className={styles.page}>
      {/* ── 상단 헤더 영역 (밤하늘 배경 적용) ── */}
      <header className={styles.header} style={{ backgroundImage: `url(${headerBg})` }}>
        <div className={styles.headerLeft}>
          <div className={styles.headerSubTitle}>스토리의 등장인물에게 목소리를 매칭해주세요</div>
          <h1 className={styles.headerTitle}>캐릭터에게<br />목소리 불어넣기</h1>
          <p className={styles.headerDesc}>
            나레이션과 캐릭터의 목소리를 골라 연결하고<br />
            잠금 버튼을 눌러 음성을 생성해 보세요.<br />
            AI가 생생한 음성을 만들어 줘요.
          </p>
        </div>
        <div className={styles.headerRight}>
          <div 
            className={styles.titleFrame} 
            ref={titleRef}
            style={{
              display: 'block',
              width: '100%',
              height: frameHeight ? `${frameHeight}px` : 'auto',
              position: 'relative'
            }}
          >
            <img 
              src={characterVoiceSvg} 
              alt="보이스 연결 타이틀 액자" 
              className={styles.titleFrameImg} 
              style={{
                width: '100%',
                height: 'auto',
                display: 'block'
              }}
            />
          </div>
        </div>
      </header>

      {/* ── 내용 컨테이너 (Glassmorphism Card) ── */}
      <div className={styles.bookContainer}>
        <div className={styles.bookContentOverlay}>
          <div className={styles.scrollArea}>
            
            {/* 사용 방법 안내 */}
            <div className={styles.infoBox}>
              <div className={styles.infoIconWrapper}>
                <img src={yarnIcon} alt="실타래 아이콘" className={styles.infoIcon} />
              </div>
              <div className={styles.infoText}>
                <h3>보이스 매핑 가이드</h3>
                <p>1. 왼쪽에서 목소리를 적용할 <b>대상</b>(나레이션·캐릭터)을 선택합니다.</p>
                <p>2. 오른쪽 보이스 라이브러리에서 사용할 <b>목소리</b>를 고릅니다.</p>
                <p>3. 연결 버튼을 누른 뒤, 잠금 버튼을 누르면 음성이 생성됩니다. (ready 상태만 연결 가능)</p>
              </div>
            </div>

            {/* 스토리 선택 바 */}
            <div className={styles.storyBar}>
              <label className={styles.label}>
                스토리 선택
                <select
                  className={styles.input}
                  value={storyId}
                  onChange={(e) => handleStoryChange(e.target.value)}
                >
                  <option value="">스토리 선택</option>
                  {stories.map((s) => (
                    <option key={s.storyId} value={s.storyId}>
                      {s.title}
                    </option>
                  ))}
                </select>
              </label>
              <p className={styles.storyHint}>
                나레이션 연결은 이 스토리에만 적용돼요. 캐릭터 목소리는 캐릭터에 저장되어 다른 스토리에서도 같이 쓰입니다.
              </p>
            </div>

            {loadError && <p className={styles.error}>{loadError}</p>}
            {message && <p className={styles.status}>{message}</p>}
            {error && <p className={styles.error}>{error}</p>}

            {storyId ? (
              <>
                <div className={styles.layout}>
                  <section className={styles.panel}>
                    <h2 className={styles.panelTitle}>목소리를 적용할 대상</h2>
                    <VoiceTargetPanel />
                  </section>
                  <section className={styles.panel}>
                    <h2 className={styles.panelTitle}>연결할 목소리 선택</h2>
                    <VoiceLibrary />
                  </section>
                </div>

                {voiceLocks.some((l) => l.ttsStatus === 'failed') ? (
                  <p className={styles.error} style={{ marginTop: 20 }}>
                    음성 생성에 실패한 대상이 있습니다. 다시 시도하거나 잠금을 해제한 뒤 다시 설정해주세요.
                  </p>
                ) : (
                  <p className={styles.statusHint}>
                    {nextStepEnabled
                      ? '모든 목소리가 잠겼어요. 음성은 백그라운드에서 준비됩니다 — 배경 단계로 넘어가도 돼요.'
                      : '나레이션과 모든 캐릭터의 목소리를 연결하고 잠가야 다음 단계로 이동할 수 있어요.'}
                  </p>
                )}
              </>
            ) : (
              <p className={styles.empty}>
                스토리를 선택하면 나레이션·등장 캐릭터에 보이스를 연결할 수 있습니다. 저장된 스토리가 없다면 먼저 “스토리 입력”에서 대본을 등록하세요.
              </p>
            )}

          </div>
          {/* ── 하단 네비게이션 고정 영역 ── */}
          <div className={styles.fixedPageNav}>
            <button className={styles.btnSecondary} onClick={() => navigate('/character')}>
              ← 이전 단계
            </button>
            <button
              className={styles.btnPrimary}
              onClick={() => navigate('/background')}
              disabled={!storyId || !nextStepEnabled}
              title={!nextStepEnabled ? '모든 목소리를 잠가야 이동할 수 있어요' : undefined}
            >
              다음 단계 →
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}


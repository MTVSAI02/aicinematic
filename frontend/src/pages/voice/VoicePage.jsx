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

// 나레이션/캐릭터에 보이스를 연결하고 대상별로 잠그는 페이지.
// 모든 필수 대상이 잠겨야 [배경 →] 이 활성화된다(잠금 시 그 대상 TTS가 백그라운드 생성).
// 씬별 TTS 듣기·타이밍 조정은 /timeline 으로 이동했다(여기서는 연결+잠금만).
export default function VoicePage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  // 스토리 자동 이어받기: ?storyId= > 현재 작업 중 스토리(useStoryStore) > 수동 선택
  const queryStoryId = searchParams.get('storyId') || ''
  const currentStoryId = useStoryStore((s) => s.storyId)

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
      // 캐릭터 매칭이 이 화면의 핵심이라, 실패를 "캐릭터 없음" 으로 숨기지 않고 표시한다
      .catch((e) =>
        setLoadError(`캐릭터 목록을 불러오지 못했습니다. ${getApiErrorMessage(e)}`)
      )
  }, [setVoices, setCharacters])

  // storyId 선택 시 해당 스토리를 store.story 로 설정.
  // 목록 응답(StoryParseResponse)이 scenes/narratorVoiceId 를 포함하므로 단건 호출 없이 찾는다.
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
      <h1>보이스</h1>
      <p className={styles.help}>
        보이스 라이브러리에 저장된 목소리를 스토리의 <b>나레이션</b>이나 <b>캐릭터</b>에 연결하는 화면이에요.
        새 목소리를 만들고 싶다면 먼저 음성 입력 페이지에서 목소리를 생성해 주세요.
      </p>

      <div className={styles.infoBox}>
        <span>1. 왼쪽에서 목소리를 적용할 <b>대상</b>(나레이션·캐릭터)을 선택합니다.</span>
        <span>2. 오른쪽 보이스 라이브러리에서 사용할 <b>목소리</b>를 고릅니다.</span>
        <span>3. 연결 버튼을 누르면 그 대상에 목소리가 적용됩니다. (ready 상태만 연결 가능)</span>
      </div>

      <div className={styles.storyBar}>
        <label className={styles.label}>
          스토리
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
        <p className={styles.hint} style={{ marginTop: 6 }}>
          나레이션 연결은 이 스토리에만 적용돼요. 캐릭터 목소리는 캐릭터에 저장되어 다른 스토리에서도 같이 쓰입니다.
        </p>
      </div>

      {loadError && <p className={styles.error}>{loadError}</p>}
      {message && <p className={styles.message}>{message}</p>}
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
            <p className={styles.error} style={{ marginTop: 16 }}>
              음성 생성에 실패한 대상이 있습니다. 다시 시도하거나 잠금을 해제한 뒤 다시 설정해주세요.
            </p>
          ) : (
            <p className={styles.hint} style={{ marginTop: 16 }}>
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

      <div className={styles.pageNav}>
        <button className={styles.btnSecondary} onClick={() => navigate('/character')}>
          ← 캐릭터
        </button>
        <button
          className={styles.btn}
          onClick={() => navigate('/background')}
          disabled={!storyId || !nextStepEnabled}
          title={!nextStepEnabled ? '모든 목소리를 잠가야 이동할 수 있어요' : undefined}
        >
          배경 →
        </button>
      </div>
    </div>
  )
}

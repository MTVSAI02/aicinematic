import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import useVoiceStore from '@/store/useVoiceStore'
import useStoryStore from '@/store/useStoryStore'
import { getVoices } from '@/api/voices'
import { getStories } from '@/api/stories'
import { getCharacters } from '@/api/characters'
import { getVoiceComfyHealth } from '@/api/ai'
import { getApiErrorMessage } from '@/utils/apiError'
import AiConnectionCheck from '@/components/AiConnectionCheck'
import VoiceTargetPanel from '@/components/voices/VoiceTargetPanel'
import VoiceLibrary from '@/components/voices/VoiceLibrary'
import styles from './VoicePage.module.css'

// 나레이션(story.narratorVoiceId)과 등장 캐릭터(character.voiceId)에 보이스를 연결하는 페이지.
// 실제 합성/클로닝/샘플 생성은 AI 단계이며, 여기서는 voiceId 연결까지만 한다.
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

  return (
    <div className={styles.page}>
      <h1>보이스</h1>
      <p className={styles.help}>
        나레이션과 등장 캐릭터에 목소리(보이스)를 연결합니다. 왼쪽에서 대상을 고르고, 오른쪽에서 보이스를 선택해 연결하세요.
        나레이션엔 나레이션용 보이스만, 캐릭터엔 캐릭터용 보이스만 연결됩니다. 실제 음성·미리듣기 샘플은 AI 단계에서 채워집니다.
      </p>

      {/* 임시: 보이스 전용 경로(프론트→백→AI 보이스 모듈→ComfyUI 읽기전용) 연결 확인.
          실제 연동 시 삭제 — TEMP_AI_CONNECTION_TEST.md */}
      <AiConnectionCheck
        check={getVoiceComfyHealth}
        label="보이스 AI 서버 연결 확인"
        okText="보이스 AI 서버 연결됨 ✅"
      />

      <div className={styles.storyBar}>
        <label className={styles.label}>
          스토리
          <select
            className={styles.input}
            value={storyId}
            onChange={(e) => setStoryId(e.target.value)}
          >
            <option value="">스토리 선택</option>
            {stories.map((s) => (
              <option key={s.storyId} value={s.storyId}>
                {s.title}
              </option>
            ))}
          </select>
        </label>
      </div>

      {loadError && <p className={styles.error}>{loadError}</p>}
      {message && <p className={styles.message}>{message}</p>}
      {error && <p className={styles.error}>{error}</p>}

      {storyId ? (
        <div className={styles.layout}>
          <section className={styles.panel}>
            <h2 className={styles.panelTitle}>연결 대상</h2>
            <VoiceTargetPanel />
          </section>
          <section className={styles.panel}>
            <h2 className={styles.panelTitle}>보이스 라이브러리</h2>
            <VoiceLibrary />
          </section>
        </div>
      ) : (
        <p className={styles.empty}>
          스토리를 선택하면 나레이션·등장 캐릭터에 보이스를 연결할 수 있습니다. 저장된 스토리가 없다면 먼저 “스토리 입력”에서 대본을 등록하세요.
        </p>
      )}

      <div className={styles.pageNav}>
        <button className={styles.btnSecondary} onClick={() => navigate('/character')}>
          ← 캐릭터
        </button>
        <button className={styles.btn} onClick={() => navigate('/background')}>
          배경 →
        </button>
      </div>
    </div>
  )
}

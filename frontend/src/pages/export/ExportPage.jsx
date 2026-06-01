import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCharacters } from '@/api/characters'
import { getStories } from '@/api/stories'
import useCharacterStore from '@/store/useCharacterStore'
import useStoryStore from '@/store/useStoryStore'
import { AudioPanel } from './AudioPanel'
import { VoiceClonePanel } from './VoiceClonePanel'
import styles from './ExportPage.module.css'
import './ExportPage.css'

function getCharacterId(character) {
  return character.characterId ?? character.id
}

function toVoiceScene(scene) {
  const segments = scene.items ?? scene.segments ?? []
  const items = segments.map((segment, index) => ({
    itemIndex: segment.itemIndex ?? index,
    type: segment.type ?? 'narration',
    speaker: segment.speaker ?? null,
    text: segment.text ?? segment.line ?? '',
    emotion: segment.emotion ?? null,
    emotionLabel: segment.emotionLabel ?? null,
  }))

  return {
    id: scene.sceneId ?? scene.id,
    order: scene.order,
    items,
    durationSec: scene.duration ?? scene.durationSec ?? 3,
    audioPath: scene.audioUrl ?? scene.audio_url,
    audioDurationSec: scene.audioDurationSec ?? scene.audio_duration_sec,
    audioItems: scene.audioItems ?? [],
  }
}

export default function ExportPage() {
  const navigate = useNavigate()
  const {
    storyId,
    storyTitle,
    scenes,
    setScenes,
    setStoryId,
    setStoryTitle,
    setSceneAudioMeta,
  } = useStoryStore()
  const {
    characters,
    selectedCharacterId,
    setCharacters,
    setCharacterVoiceProfile,
  } = useCharacterStore()
  const [stories, setStories] = useState([])
  const [selectedStoryId, setSelectedStoryId] = useState(storyId ?? '')
  const [isLoadingStories, setIsLoadingStories] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [jobId, setJobId] = useState(null)
  const [progress, setProgress] = useState(0)
  const [done, setDone] = useState(false)

  useEffect(() => {
    let ignore = false

    async function loadBackendData() {
      setIsLoadingStories(true)
      setLoadError('')

      try {
        const [storyList, characterList] = await Promise.all([
          getStories(),
          getCharacters(),
        ])

        if (ignore) return
        setStories(Array.isArray(storyList) ? storyList : [])
        setCharacters(Array.isArray(characterList) ? characterList : [])
      } catch (error) {
        if (ignore) return
        setLoadError(
          error instanceof Error
            ? error.message
            : '백엔드에서 스토리 정보를 불러오지 못했습니다.',
        )
      } finally {
        if (!ignore) {
          setIsLoadingStories(false)
        }
      }
    }

    loadBackendData()

    return () => {
      ignore = true
    }
  }, [setCharacters])

  const effectiveStoryId = selectedStoryId || storyId || ''
  const selectedStory = stories.find((story) => story.storyId === effectiveStoryId)

  useEffect(() => {
    if (!selectedStory) return
    setStoryId(selectedStory.storyId)
    setStoryTitle(selectedStory.title)
    setScenes(selectedStory.scenes)
  }, [selectedStory, setScenes, setStoryId, setStoryTitle])

  const displayScenes =
    effectiveStoryId === storyId && scenes.length > 0
      ? scenes
      : selectedStory?.scenes ?? []
  const voiceScenes = displayScenes.map(toVoiceScene)
  const currentStoryId = selectedStory?.storyId ?? ''
  const currentStoryTitle = selectedStory?.title ?? storyTitle

  const characterNameById = useMemo(() => {
    return characters.reduce((result, character) => {
      result[getCharacterId(character)] = character.name
      return result
    }, {})
  }, [characters])

  function updateSceneAudio(sceneId, audio) {
    setSceneAudioMeta(
      sceneId,
      audio.audioPath,
      audio.audioDurationSec,
      audio.audioItems,
    )
  }

  async function handleRender() {
    setJobId('mock-job-1')
    setProgress(0)
    setDone(false)

    let nextProgress = 0
    const interval = setInterval(() => {
      nextProgress += 20
      setProgress(nextProgress)

      if (nextProgress >= 100) {
        clearInterval(interval)
        setDone(true)
      }
    }, 600)
  }

  return (
    <div className={styles.page}>
      <h1>출력</h1>
      <p className={styles.guide}>
        백엔드에 저장된 스토리를 선택하고, 씬별 TTS 음성을 생성한 뒤 최종
        영상을 렌더링합니다.
      </p>

      <section className="panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Backend Story</p>
            <h2>스토리 선택</h2>
          </div>
          <p className="panel-description">
            실제 TTS는 백엔드에 저장된 <code>story_mock_*</code> 스토리에서만
            생성됩니다.
          </p>
        </div>

        {isLoadingStories ? (
          <p className="empty-message">스토리 목록을 불러오는 중입니다.</p>
        ) : (
          <>
            <label className="story-select-label">
              스토리
              <select
                className="story-select"
                value={effectiveStoryId}
                onChange={(event) => setSelectedStoryId(event.target.value)}
              >
                <option value="">스토리를 선택하세요</option>
                {stories.map((story) => (
                  <option key={story.storyId} value={story.storyId}>
                    {story.title} ({story.storyId})
                  </option>
                ))}
              </select>
            </label>

            {currentStoryId && (
              <p className="selected-story-summary">
                선택된 스토리: <strong>{currentStoryTitle}</strong> ·{' '}
                {currentStoryId} · 씬 {displayScenes.length}개
              </p>
            )}
          </>
        )}

        {loadError && <p className="error-message">{loadError}</p>}

        {!isLoadingStories && stories.length === 0 && (
          <div className="empty-state">
            <p>
              백엔드에 저장된 스토리가 없습니다. 먼저 스토리 입력에서 씬
              분해를 진행해 주세요.
            </p>
            <button
              className="primary-button"
              type="button"
              onClick={() => navigate('/story-input')}
            >
              스토리 입력으로 이동
            </button>
          </div>
        )}

        {!isLoadingStories && stories.length > 0 && !currentStoryId && (
          <p className="empty-message">
            스토리를 선택하면 해당 씬 목록으로 음성을 생성할 수 있습니다.
          </p>
        )}
      </section>

      {currentStoryId && (
        <AudioPanel
          storyId={currentStoryId}
          scenes={voiceScenes}
          characterNameById={characterNameById}
          onSceneAudioGenerated={updateSceneAudio}
        />
      )}

      <VoiceClonePanel
        characters={characters}
        selectedCharacterId={selectedCharacterId}
        onVoiceProfileSaved={setCharacterVoiceProfile}
      />

      {!jobId ? (
        <button
          className={styles.btn}
          disabled={!currentStoryId}
          onClick={handleRender}
        >
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

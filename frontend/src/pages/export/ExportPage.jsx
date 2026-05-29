import { useEffect, useMemo, useState } from 'react'
import { mockCharacters, mockStoreScenes } from '@/api/mockData'
import useCharacterStore from '@/store/useCharacterStore'
import useStoryStore from '@/store/useStoryStore'
import { AudioPanel } from './AudioPanel'
import { VoiceClonePanel } from './VoiceClonePanel'
import styles from './ExportPage.module.css'
import './ExportPage.css'

const FALLBACK_STORY_ID = 'story_001'

function toVoiceScene(scene) {
  const firstSegment = scene.segments?.[0] ?? {
    type: 'narration',
    speaker: null,
    text: '',
  }

  return {
    id: scene.id,
    order: scene.order,
    type: firstSegment.type,
    speaker: firstSegment.speaker,
    line: scene.segments?.map((segment) => segment.text).join(' ') ?? '',
    durationSec: scene.duration,
    audioPath: scene.audio_url,
    audioDurationSec: scene.audio_duration_sec,
  }
}

export default function ExportPage() {
  const {
    storyId,
    scenes,
    setScenes,
    setSceneAudioMeta,
  } = useStoryStore()
  const {
    characters,
    selectedCharacterId,
    setCharacterVoiceProfile,
  } = useCharacterStore()
  const [jobId, setJobId] = useState(null)
  const [progress, setProgress] = useState(0)
  const [done, setDone] = useState(false)

  useEffect(() => {
    if (scenes.length === 0) {
      setScenes(mockStoreScenes)
    }
  }, [scenes.length, setScenes])

  const displayScenes = scenes.length > 0 ? scenes : mockStoreScenes
  const displayCharacters = characters.length > 0 ? characters : mockCharacters
  const voiceScenes = displayScenes.map(toVoiceScene)
  const currentStoryId = storyId ?? FALLBACK_STORY_ID

  const characterNameById = useMemo(() => {
    return displayCharacters.reduce((result, character) => {
      result[character.id] = character.name
      return result
    }, {})
  }, [displayCharacters])

  function updateSceneAudio(sceneId, audio) {
    setSceneAudioMeta(sceneId, audio.audioPath, audio.audioDurationSec)
  }

  async function handleRender() {
    // TODO: POST /render → polling GET /render/{job_id}/status
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
        씬별 음성을 생성하고 미리들은 뒤, 완성 영상을 렌더링하세요.
      </p>

      <AudioPanel
        storyId={currentStoryId}
        scenes={voiceScenes}
        characterNameById={characterNameById}
        onSceneAudioGenerated={updateSceneAudio}
      />

      <VoiceClonePanel
        characters={displayCharacters}
        selectedCharacterId={selectedCharacterId}
        onVoiceProfileSaved={setCharacterVoiceProfile}
      />

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

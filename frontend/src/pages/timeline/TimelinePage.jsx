import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { mockStoreScenes } from '@/api/mockData'
import { updateSceneDuration as updateSceneDurationApi } from '@/api/timelineApi'
import useStoryStore from '@/store/useStoryStore'
import styles from './TimelinePage.module.css'

const DEFAULT_DURATION = 3
const MIN_DURATION_SEC = 1
const AUDIO_TAIL_PADDING_SEC = 0.5

function getSceneId(scene) {
  return scene.sceneId ?? scene.id
}

function getSceneText(scene) {
  if (scene.items?.length) {
    return scene.items.map((item) => item.text).join(' ')
  }
  return scene.segments?.map((segment) => segment.text).join(' ') ?? ''
}

function getSceneDuration(scene) {
  return scene.duration ?? scene.durationSec ?? DEFAULT_DURATION
}

function getAudioDuration(scene) {
  return scene.audioDurationSec ?? scene.audio_duration_sec ?? null
}

function getAudioSafeDuration(scene) {
  const audioDuration = getAudioDuration(scene)
  return audioDuration ? audioDuration + AUDIO_TAIL_PADDING_SEC : MIN_DURATION_SEC
}

function normalizeDuration(value, scene) {
  const parsedValue = Number.parseFloat(value)
  const requestedDuration = Number.isFinite(parsedValue)
    ? parsedValue
    : MIN_DURATION_SEC

  return Number(
    Math.max(MIN_DURATION_SEC, requestedDuration, getAudioSafeDuration(scene)).toFixed(1),
  )
}

export default function TimelinePage() {
  const navigate = useNavigate()
  const { storyId, scenes, setScenes, updateSceneDuration } = useStoryStore()
  const [saveMessages, setSaveMessages] = useState({})

  useEffect(() => {
    if (scenes.length === 0) {
      setScenes(mockStoreScenes)
    }
  }, [scenes.length, setScenes])

  const displayScenes = scenes.length > 0 ? scenes : mockStoreScenes
  const total = displayScenes.reduce(
    (acc, scene) => acc + getSceneDuration(scene),
    0,
  )

  async function handleDurationChange(scene, value) {
    const sceneId = getSceneId(scene)
    const safeDuration = normalizeDuration(value, scene)

    updateSceneDuration(sceneId, safeDuration)
    setSaveMessages((current) => ({
      ...current,
      [sceneId]: '저장 중...',
    }))

    try {
      await updateSceneDurationApi({
        storyId: storyId ?? 'story_001',
        sceneId,
        durationSec: safeDuration,
      })

      setSaveMessages((current) => ({
        ...current,
        [sceneId]:
          safeDuration > Number.parseFloat(value)
            ? `음성 길이에 맞춰 ${safeDuration.toFixed(1)}초로 보정했습니다.`
            : '길이를 저장했습니다.',
      }))
    } catch (error) {
      setSaveMessages((current) => ({
        ...current,
        [sceneId]:
          error instanceof Error ? error.message : '길이 저장에 실패했습니다.',
      }))
    }
  }

  if (displayScenes.length === 0) {
    return (
      <div className={styles.page}>
        <h1>타임라인</h1>
        <p className={styles.empty}>씬이 없습니다. 스토리를 먼저 입력해 주세요.</p>
        <button className={styles.btn} onClick={() => navigate('/story-input')}>
          스토리 입력하러 가기
        </button>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <h1>타임라인</h1>
      <p className={styles.guide}>
        씬 순서와 재생 길이를 조절하세요. 총 {total.toFixed(1)}초
      </p>

      <div className={styles.track}>
        {displayScenes.map((scene) => {
          const sceneId = getSceneId(scene)
          const duration = getSceneDuration(scene)

          return (
            <div key={sceneId} className={styles.clip} style={{ flex: duration }}>
              <span className={styles.clipOrder}>#{scene.order}</span>
              <span className={styles.clipDuration}>{duration.toFixed(1)}s</span>
            </div>
          )
        })}
      </div>

      <ul className={styles.list}>
        {displayScenes.map((scene) => {
          const sceneId = getSceneId(scene)
          const duration = getSceneDuration(scene)
          const audioDuration = getAudioDuration(scene)

          return (
            <li key={sceneId} className={styles.row}>
              <span className={styles.rowOrder}>#{scene.order}</span>
              <span className={styles.rowText}>{getSceneText(scene)}</span>
              <span className={styles.audioText}>
                음성 {audioDuration ? `${audioDuration.toFixed(1)}초` : '-'}
              </span>
              <input
                className={styles.durationInput}
                type="number"
                min="1"
                step="0.1"
                value={duration}
                onChange={(event) =>
                  handleDurationChange(scene, event.target.value)
                }
              />
              <span className={styles.unit}>초</span>
              {saveMessages[sceneId] && (
                <span className={styles.saveMessage}>{saveMessages[sceneId]}</span>
              )}
            </li>
          )
        })}
      </ul>

      <div className={styles.actions}>
        <button
          className={styles.btnSecondary}
          onClick={() => navigate('/scene-editor')}
        >
          씬 편집
        </button>
        <button className={styles.btn} onClick={() => navigate('/export')}>
          출력 준비
        </button>
      </div>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { mockStoreScenes } from '@/api/mockData'
import { updateSceneDuration as updateSceneDurationApi } from '@/api/timelineApi'
import useStoryStore from '@/store/useStoryStore'
import styles from './TimelinePage.module.css'

const MIN_DURATION_SEC = 1
const AUDIO_TAIL_PADDING_SEC = 0.5

function getSceneText(scene) {
  return scene.segments?.map((segment) => segment.text).join(' ') ?? ''
}

function getAudioSafeDuration(scene) {
  return scene.audio_duration_sec
    ? scene.audio_duration_sec + AUDIO_TAIL_PADDING_SEC
    : MIN_DURATION_SEC
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
  const {
    storyId,
    scenes,
    setScenes,
    updateSceneDuration,
  } = useStoryStore()
  const [saveMessages, setSaveMessages] = useState({})

  useEffect(() => {
    if (scenes.length === 0) {
      setScenes(mockStoreScenes)
    }
  }, [scenes.length, setScenes])

  const displayScenes = scenes.length > 0 ? scenes : mockStoreScenes
  const total = displayScenes.reduce((acc, scene) => acc + scene.duration, 0)

  async function handleDurationChange(scene, value) {
    const safeDuration = normalizeDuration(value, scene)

    updateSceneDuration(scene.id, safeDuration)
    setSaveMessages((current) => ({
      ...current,
      [scene.id]: '저장 중...',
    }))

    try {
      await updateSceneDurationApi({
        storyId: storyId ?? 'story_001',
        sceneId: scene.id,
        durationSec: safeDuration,
      })

      setSaveMessages((current) => ({
        ...current,
        [scene.id]:
          safeDuration > Number.parseFloat(value)
            ? `음성 길이에 맞춰 ${safeDuration.toFixed(1)}초로 보정했습니다.`
            : '길이를 저장했습니다.',
      }))
    } catch (error) {
      setSaveMessages((current) => ({
        ...current,
        [scene.id]:
          error instanceof Error ? error.message : '길이 저장에 실패했습니다.',
      }))
    }
  }

  if (displayScenes.length === 0) {
    return (
      <div className={styles.page}>
        <h1>타임라인</h1>
        <p className={styles.empty}>씬이 없어요. 스토리를 먼저 입력해주세요.</p>
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
        {displayScenes.map((scene) => (
          <div
            key={scene.id}
            className={styles.clip}
            style={{ flex: scene.duration }}
          >
            <span className={styles.clipOrder}>씬 {scene.order}</span>
            <span className={styles.clipDuration}>{scene.duration}s</span>
          </div>
        ))}
      </div>

      <ul className={styles.list}>
        {displayScenes.map((scene) => (
          <li key={scene.id} className={styles.row}>
            <span className={styles.rowOrder}>씬 {scene.order}</span>
            <span className={styles.rowText}>{getSceneText(scene)}</span>
            <span className={styles.audioText}>
              음성 {scene.audio_duration_sec ? `${scene.audio_duration_sec.toFixed(1)}초` : '-'}
            </span>
            <input
              className={styles.durationInput}
              type="number"
              min="1"
              step="0.1"
              value={scene.duration}
              onChange={(event) =>
                handleDurationChange(scene, event.target.value)
              }
            />
            <span className={styles.unit}>초</span>
            {saveMessages[scene.id] && (
              <span className={styles.saveMessage}>{saveMessages[scene.id]}</span>
            )}
          </li>
        ))}
      </ul>

      <div className={styles.actions}>
        <button
          className={styles.btnSecondary}
          onClick={() => navigate('/scene-editor')}
        >
          ← 씬 편집
        </button>
        <button className={styles.btn} onClick={() => navigate('/export')}>
          출력 →
        </button>
      </div>
    </div>
  )
}

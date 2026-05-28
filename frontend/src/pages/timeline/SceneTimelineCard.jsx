import { useState } from 'react'
import { updateSceneDuration } from '../../api/timelineApi'

const MIN_DURATION_SEC = 1
const AUDIO_TAIL_PADDING_SEC = 0.5

function getSpeakerLabel(scene, characterNameById) {
  if (scene.type === 'narration') return '내레이터'
  return characterNameById[scene.speaker] ?? scene.speaker ?? '알 수 없음'
}

function getMinimumDuration(scene) {
  const audioSafeDuration = scene.audioDurationSec
    ? scene.audioDurationSec + AUDIO_TAIL_PADDING_SEC
    : MIN_DURATION_SEC

  return Math.max(MIN_DURATION_SEC, audioSafeDuration)
}

function normalizeDuration(value, scene) {
  const parsedValue = Number.parseFloat(value)
  const requestedDuration = Number.isFinite(parsedValue)
    ? parsedValue
    : MIN_DURATION_SEC
  const safeDuration = Math.max(requestedDuration, getMinimumDuration(scene))

  return Number(safeDuration.toFixed(1))
}

export function SceneTimelineCard({
  storyId,
  scene,
  characterNameById,
  onSceneDurationChange,
}) {
  const [draftDuration, setDraftDuration] = useState(
    scene.durationSec.toFixed(1),
  )
  const [statusMessage, setStatusMessage] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  const minimumDuration = getMinimumDuration(scene)
  const isAudioTooLong =
    scene.audioDurationSec && scene.durationSec < minimumDuration

  async function commitDuration(nextValue) {
    const safeDuration = normalizeDuration(nextValue, scene)
    setDraftDuration(safeDuration.toFixed(1))
    setIsSaving(true)

    try {
      await updateSceneDuration({
        storyId,
        sceneId: scene.id,
        durationSec: safeDuration,
      })
      onSceneDurationChange(scene.id, safeDuration)

      if (safeDuration > Number.parseFloat(nextValue)) {
        setStatusMessage(
          `음성 길이에 맞춰 ${safeDuration.toFixed(1)}초로 보정했습니다.`,
        )
      } else {
        setStatusMessage('길이를 저장했습니다.')
      }
    } catch (error) {
      setStatusMessage(
        error instanceof Error ? error.message : '길이 저장에 실패했습니다.',
      )
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <article className="timeline-card">
      <div className="timeline-card-head">
        <span className="scene-order">Scene {scene.order}</span>
        <span className={scene.audioPath ? 'voice-chip done' : 'voice-chip'}>
          {scene.audioPath ? '음성 완료' : '음성 전'}
        </span>
      </div>

      <div className="timeline-card-body">
        <p className="timeline-speaker">
          {scene.type === 'narration' ? '내레이션' : '대사'} ·{' '}
          {getSpeakerLabel(scene, characterNameById)}
        </p>
        <p className="timeline-line">{scene.line}</p>
      </div>

      <label className="duration-field">
        <span>장면 길이</span>
        <div>
          <input
            min={MIN_DURATION_SEC}
            step="0.1"
            type="number"
            value={draftDuration}
            onBlur={(event) => commitDuration(event.target.value)}
            onChange={(event) => setDraftDuration(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.currentTarget.blur()
              }
            }}
          />
          <span>초</span>
        </div>
      </label>

      <div className="timeline-stats">
        <span>현재 {scene.durationSec.toFixed(1)}초</span>
        <span>
          음성{' '}
          {scene.audioDurationSec ? `${scene.audioDurationSec.toFixed(1)}초` : '-'}
        </span>
      </div>

      {(statusMessage || isAudioTooLong || isSaving) && (
        <p className="timeline-message">
          {isSaving
            ? '저장 중...'
            : statusMessage ||
              `음성보다 짧아 최소 ${minimumDuration.toFixed(1)}초가 필요합니다.`}
        </p>
      )}
    </article>
  )
}

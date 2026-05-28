import { useState } from 'react'
import { generateSceneVoice } from '../../api/voiceApi'

function getSpeakerLabel(scene, characterNameById) {
  if (scene.type === 'narration') return '내레이터'
  return characterNameById[scene.speaker] ?? scene.speaker ?? '알 수 없음'
}

function getVoiceLabel(scene, characterNameById) {
  if (scene.type === 'narration') return '내레이터 목소리'
  return `${getSpeakerLabel(scene, characterNameById)} 캐릭터 목소리`
}

export function AudioPanel({
  storyId,
  scenes,
  characterNameById,
  onSceneAudioGenerated,
}) {
  const [sceneStatuses, setSceneStatuses] = useState({})

  async function handleGenerateVoice(scene) {
    setSceneStatuses((current) => ({
      ...current,
      [scene.id]: { state: 'loading', message: '음성을 생성하는 중입니다.' },
    }))

    try {
      const audio = await generateSceneVoice({ storyId, scene })
      onSceneAudioGenerated(scene.id, audio)
      setSceneStatuses((current) => ({
        ...current,
        [scene.id]: { state: 'done', message: '음성 생성 완료' },
      }))
    } catch (error) {
      setSceneStatuses((current) => ({
        ...current,
        [scene.id]: {
          state: 'error',
          message: error instanceof Error ? error.message : '음성 생성 실패',
        },
      }))
    }
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">R-40 · R-41</p>
          <h2>TTS 음성 생성</h2>
        </div>
        <p className="panel-description">
          내레이션은 내레이터 목소리, 대사는 캐릭터 목소리로 구분합니다.
        </p>
      </div>

      <div className="scene-list">
        {scenes.map((scene) => {
          const status = sceneStatuses[scene.id] ?? {
            state: 'idle',
            message: '음성 생성 전',
          }
          const isLoading = status.state === 'loading'
          const speakerLabel = getSpeakerLabel(scene, characterNameById)

          return (
            <article className="scene-card" key={scene.id}>
              <div className="scene-card-top">
                <span className="scene-order">Scene {scene.order}</span>
                <span className={`status-badge status-${status.state}`}>
                  {status.message}
                </span>
              </div>

              <div className="scene-meta">
                <span>{scene.type === 'narration' ? '내레이션' : '대사'}</span>
                <span>{speakerLabel}</span>
                <span>{getVoiceLabel(scene, characterNameById)}</span>
              </div>

              <p className="scene-line">{scene.line}</p>

              <div className="scene-timing">
                <span>장면 길이 {scene.durationSec.toFixed(1)}초</span>
                <span>
                  음성 길이{' '}
                  {scene.audioDurationSec
                    ? `${scene.audioDurationSec.toFixed(1)}초`
                    : '-'}
                </span>
              </div>

              <div className="scene-actions">
                <button
                  className="primary-button"
                  type="button"
                  disabled={isLoading}
                  onClick={() => handleGenerateVoice(scene)}
                >
                  {scene.audioPath ? '음성 다시 생성' : '음성 생성'}
                </button>

                {scene.audioPath && (
                  <audio className="audio-player" controls src={scene.audioPath}>
                    이 브라우저는 오디오 재생을 지원하지 않습니다.
                  </audio>
                )}
              </div>
            </article>
          )
        })}
      </div>
    </section>
  )
}

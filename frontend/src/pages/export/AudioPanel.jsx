import { useState } from 'react'
import { generateSceneVoice } from '@/api/voiceApi'

function getSpeakerLabel(item, characterNameById) {
  if (item.type === 'narration') return '나레이터'
  return characterNameById[item.speaker] ?? item.speaker ?? '화자 없음'
}

function getVoiceLabel(item, characterNameById) {
  if (item.type === 'narration') return '나레이터 목소리'
  return `${getSpeakerLabel(item, characterNameById)} 캐릭터 목소리`
}

function getAudioForItem(item, audioItems) {
  return audioItems.find((audio) => audio.itemIndex === item.itemIndex)
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
      [scene.id]: {
        state: 'loading',
        message: '씬 안의 나레이션과 대사를 생성하는 중입니다.',
        audioItems: current[scene.id]?.audioItems ?? scene.audioItems ?? [],
      },
    }))

    try {
      const audio = await generateSceneVoice({ storyId, scene })
      onSceneAudioGenerated(scene.id, audio)
      setSceneStatuses((current) => ({
        ...current,
        [scene.id]: {
          state: 'done',
          message: '음성 생성 완료',
          audioItems: audio.audioItems,
        },
      }))
    } catch (error) {
      setSceneStatuses((current) => ({
        ...current,
        [scene.id]: {
          state: 'error',
          message: error instanceof Error ? error.message : '음성 생성 실패',
          audioItems: current[scene.id]?.audioItems ?? scene.audioItems ?? [],
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
          한 씬 안의 나레이션과 캐릭터 대사를 각각 분리해서 생성하고
          미리듣기합니다.
        </p>
      </div>

      {scenes.length === 0 ? (
        <p className="empty-message">선택한 스토리에 생성할 씬이 없습니다.</p>
      ) : (
        <div className="scene-list">
          {scenes.map((scene) => {
            const status = sceneStatuses[scene.id] ?? {
              state: 'idle',
              message: '음성 생성 전',
              audioItems: scene.audioItems ?? [],
            }
            const isLoading = status.state === 'loading'
            const audioItems = status.audioItems ?? scene.audioItems ?? []

            return (
              <article className="scene-card" key={scene.id}>
                <div className="scene-card-top">
                  <span className="scene-order">Scene {scene.order}</span>
                  <span className={`status-badge status-${status.state}`}>
                    {status.message}
                  </span>
                </div>

                <div className="tts-item-list">
                  {scene.items.map((item) => {
                    const itemAudio = getAudioForItem(item, audioItems)

                    return (
                      <div className="tts-item" key={item.itemIndex}>
                        <div className="scene-meta">
                          <span>
                            {item.type === 'narration' ? '나레이션' : '대사'}
                          </span>
                          <span>{getSpeakerLabel(item, characterNameById)}</span>
                          <span>{getVoiceLabel(item, characterNameById)}</span>
                          {item.emotionLabel && <span>{item.emotionLabel}</span>}
                        </div>

                        <p className="scene-line">{item.text}</p>

                        {itemAudio?.error && (
                          <p className="tts-item-error">{itemAudio.error}</p>
                        )}

                        {itemAudio?.audioUrl && (
                          <div className="tts-item-audio">
                            <span>
                              음성 길이{' '}
                              {itemAudio.durationSec
                                ? `${itemAudio.durationSec.toFixed(1)}초`
                                : '-'}
                            </span>
                            <audio
                              className="audio-player"
                              controls
                              src={itemAudio.audioUrl}
                            >
                              브라우저가 오디오 재생을 지원하지 않습니다.
                            </audio>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>

                <div className="scene-timing">
                  <span>씬 길이 {scene.durationSec.toFixed(1)}초</span>
                  <span>대사 항목 {scene.items.length}개</span>
                </div>

                <div className="scene-actions">
                  <button
                    className="primary-button"
                    type="button"
                    disabled={isLoading}
                    onClick={() => handleGenerateVoice(scene)}
                  >
                    {audioItems.some((audio) => audio.audioUrl)
                      ? '씬 음성 다시 생성'
                      : '씬 음성 생성'}
                  </button>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}

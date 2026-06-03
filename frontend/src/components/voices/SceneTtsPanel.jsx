import { useState } from 'react'
import { generateSceneTts } from '@/api/tts'
import styles from '@/pages/voice/VoicePage.module.css'

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

export default function SceneTtsPanel({
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
      const audio = await generateSceneTts({ storyId, scene })
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
    <section className={styles.ttsPanel}>
      <div className={styles.ttsHeader}>
        <div>
          <p className={styles.eyebrow}>TTS</p>
          <h2 className={styles.panelTitle}>씬별 음성 생성/출력</h2>
        </div>
        <p className={styles.ttsDescription}>
          연결된 보이스 정보를 기준으로 씬 안의 나레이션과 대사를 각각 생성하고 바로 미리듣기합니다.
        </p>
      </div>

      {scenes.length === 0 ? (
        <p className={styles.empty}>선택한 스토리에 생성할 씬이 없습니다.</p>
      ) : (
        <div className={styles.ttsSceneList}>
          {scenes.map((scene) => {
            const status = sceneStatuses[scene.id] ?? {
              state: 'idle',
              message: '음성 생성 전',
              audioItems: scene.audioItems ?? [],
            }
            const isLoading = status.state === 'loading'
            const audioItems = status.audioItems ?? scene.audioItems ?? []

            return (
              <article className={styles.ttsSceneCard} key={scene.id}>
                <div className={styles.ttsSceneTop}>
                  <span className={styles.sceneOrder}>Scene {scene.order}</span>
                  <span className={`${styles.statusBadge} ${styles[`status_${status.state}`]}`}>
                    {status.message}
                  </span>
                </div>

                <div className={styles.ttsItemList}>
                  {scene.items.map((item) => {
                    const itemAudio = getAudioForItem(item, audioItems)

                    return (
                      <div className={styles.ttsItem} key={item.itemIndex}>
                        <div className={styles.sceneMeta}>
                          <span>{item.type === 'narration' ? '나레이션' : '대사'}</span>
                          <span>{getSpeakerLabel(item, characterNameById)}</span>
                          <span>{getVoiceLabel(item, characterNameById)}</span>
                          {item.emotionLabel && <span>{item.emotionLabel}</span>}
                        </div>

                        <p className={styles.sceneLine}>{item.text}</p>

                        {itemAudio?.error && (
                          <p className={styles.ttsItemError}>{itemAudio.error}</p>
                        )}

                        {itemAudio?.audioUrl && (
                          <div className={styles.ttsItemAudio}>
                            <span>
                              음성 길이{' '}
                              {itemAudio.durationSec
                                ? `${itemAudio.durationSec.toFixed(1)}초`
                                : '-'}
                            </span>
                            <audio
                              className={styles.audioPlayer}
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

                <div className={styles.sceneTiming}>
                  <span>씬 길이 {scene.durationSec.toFixed(1)}초</span>
                  <span>대사 항목 {scene.items.length}개</span>
                </div>

                <div className={styles.ttsActions}>
                  <button
                    className={styles.btn}
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

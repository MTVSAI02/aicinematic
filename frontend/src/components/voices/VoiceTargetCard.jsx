import useVoiceStore from '@/store/useVoiceStore'
import { assignNarratorVoiceToStory } from '@/api/stories'
import { assignVoiceToCharacter } from '@/api/characters'
import { getApiErrorMessage } from '@/utils/apiError'
import styles from '@/pages/voice/VoicePage.module.css'

// 보이스를 붙일 대상(나레이션 또는 등장 캐릭터) 카드.
// 클릭하면 selectedTarget 으로 선택되고, 오른쪽 라이브러리에서 보이스를 고를 수 있다.
export default function VoiceTargetCard({ target }) {
  const story = useVoiceStore((s) => s.story)
  const voices = useVoiceStore((s) => s.voices)
  const characters = useVoiceStore((s) => s.characters)
  const selectedTarget = useVoiceStore((s) => s.selectedTarget)
  const setSelectedTarget = useVoiceStore((s) => s.setSelectedTarget)
  const setNarratorVoiceId = useVoiceStore((s) => s.setNarratorVoiceId)
  const setCharacterVoiceId = useVoiceStore((s) => s.setCharacterVoiceId)
  const setMessage = useVoiceStore((s) => s.setMessage)
  const setError = useVoiceStore((s) => s.setError)

  const isNarrator = target.type === 'narrator'
  const selectable = isNarrator || target.matched

  // 현재 연결된 voiceId / 표시 이름
  const currentVoiceId = isNarrator
    ? story?.narratorVoiceId ?? null
    : characters.find((c) => c.characterId === target.characterId)?.voiceId ?? null
  const currentVoiceName = voices.find((v) => v.voiceId === currentVoiceId)?.name

  const isSelected =
    selectedTarget &&
    (isNarrator
      ? selectedTarget.type === 'narrator'
      : selectedTarget.type === 'character' &&
        selectedTarget.characterId === target.characterId)

  function handleSelect() {
    if (!selectable) return
    setSelectedTarget({
      type: target.type,
      name: target.name,
      characterId: target.characterId,
      accept: isNarrator ? 'narrator' : 'character',
    })
  }

  async function handleUnassign(e) {
    e.stopPropagation()
    setError(null)
    try {
      if (isNarrator) {
        await assignNarratorVoiceToStory(story.storyId, { voiceId: null })
        setNarratorVoiceId(null)
      } else {
        await assignVoiceToCharacter(target.characterId, { voiceId: null })
        setCharacterVoiceId(target.characterId, null)
      }
      setMessage(`${target.name} 보이스 연결을 해제했습니다.`)
    } catch (err) {
      setMessage(null)
      setError(getApiErrorMessage(err))
    }
  }

  return (
    <div
      className={`${styles.targetCard} ${isSelected ? styles.targetCardSelected : ''} ${
        selectable ? '' : styles.targetCardDisabled
      }`}
      onClick={handleSelect}
    >
      <div className={styles.targetHead}>
        <span className={styles.targetName}>{target.name}</span>
        <span className={styles.badge}>{isNarrator ? '나레이션' : '캐릭터'}</span>
      </div>

      <span className={styles.voiceDesc}>
        {isNarrator ? '이야기를 읽어주는 목소리' : '등장인물 대사 목소리'}
      </span>

      {!isNarrator &&
        (target.matched ? (
          <span className={styles.voiceMeta}>{target.characterId}</span>
        ) : (
          <span className={styles.validation}>
            저장된 캐릭터 없음 · 먼저 “캐릭터”에서 생성/저장해주세요
          </span>
        ))}

      <span className={styles.currentVoice}>
        현재 목소리: {currentVoiceId ? currentVoiceName ?? currentVoiceId : '목소리 미설정'}
      </span>

      {selectable && currentVoiceId && (
        <div className={styles.cardActions} onClick={(e) => e.stopPropagation()}>
          <button className={styles.cardBtn} onClick={handleUnassign}>
            연결 해제
          </button>
        </div>
      )}

      {isSelected && (
        <span className={styles.selectedBadge}>선택됨 · 오른쪽에서 보이스를 고르세요</span>
      )}
    </div>
  )
}

import useVoiceStore from '@/store/useVoiceStore'
import VoiceTargetCard from './VoiceTargetCard'
import styles from '@/pages/voice/VoicePage.module.css'

// 보이스를 적용할 대상(나레이션 + 등장 캐릭터) 목록.
// 대상/상태는 백엔드 GET /voice-locks 결과(store.voiceLocks)로 그린다.
export default function VoiceTargetPanel() {
  const voiceLocks = useVoiceStore((s) => s.voiceLocks)

  if (!voiceLocks.length) {
    return <p className={styles.validation}>연결할 대상이 없습니다.</p>
  }

  const narration = voiceLocks.filter((l) => l.targetType === 'narration')
  const characters = voiceLocks.filter((l) => l.targetType === 'character')

  return (
    <div className={styles.targetList}>
      {narration.length > 0 && (
        <>
          <h3 className={styles.sectionTitle}>나레이션</h3>
          {narration.map((lock) => (
            <VoiceTargetCard key={lock.targetId} lock={lock} />
          ))}
        </>
      )}

      <h3 className={styles.sectionTitle}>등장 캐릭터</h3>
      {characters.length === 0 ? (
        <p className={styles.validation}>이 스토리에는 대사(dialogue) 화자가 없습니다.</p>
      ) : (
        characters.map((lock) => (
          <VoiceTargetCard key={`${lock.targetType}:${lock.targetId}`} lock={lock} />
        ))
      )}
    </div>
  )
}

import useVoiceStore from '@/store/useVoiceStore'
import VoiceTargetCard from './VoiceTargetCard'
import styles from '@/pages/voice/VoicePage.module.css'

// 스토리 scenes 의 dialogue speaker 를 등장 순서대로 중복 없이 추출한다.
function extractSpeakers(story) {
  const speakers = []
  for (const scene of story?.scenes ?? []) {
    for (const item of scene.items ?? []) {
      if (item.type === 'dialogue' && item.speaker && !speakers.includes(item.speaker)) {
        speakers.push(item.speaker)
      }
    }
  }
  return speakers
}

export default function VoiceTargetPanel() {
  const story = useVoiceStore((s) => s.story)
  const characters = useVoiceStore((s) => s.characters)

  if (!story) return null

  const speakers = extractSpeakers(story)

  return (
    <div className={styles.targetList}>
      <h3 className={styles.sectionTitle}>나레이션</h3>
      <VoiceTargetCard target={{ type: 'narrator', name: '나레이션' }} />

      <h3 className={styles.sectionTitle}>등장 캐릭터</h3>
      {speakers.length === 0 ? (
        <p className={styles.validation}>이 스토리에는 대사(dialogue) 화자가 없습니다.</p>
      ) : (
        speakers.map((speaker) => {
          const matched = characters.find((c) => c.name === speaker)
          return (
            <VoiceTargetCard
              key={speaker}
              target={{
                type: 'character',
                name: speaker,
                characterId: matched?.characterId ?? null,
                matched: Boolean(matched),
              }}
            />
          )
        })
      )}
    </div>
  )
}

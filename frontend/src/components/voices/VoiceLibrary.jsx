import useVoiceStore from '@/store/useVoiceStore'
import VoiceCard from './VoiceCard'
import VoiceCreateForm from './VoiceCreateForm'
import styles from '@/pages/voice/VoicePage.module.css'

// 보이스 라이브러리: 기본 나레이션(narrator preset) / 내 보이스(character) 섹션 + 생성 폼.
// 연결 가능 여부는 VoiceCard 가 selectedTarget.accept 와 voiceType 을 비교해 판단한다.
export default function VoiceLibrary() {
  const voices = useVoiceStore((s) => s.voices)
  const selectedTarget = useVoiceStore((s) => s.selectedTarget)

  const narratorVoices = voices.filter((v) => v.voiceType === 'narrator')
  const characterVoices = voices.filter((v) => v.voiceType === 'character')

  return (
    <div>
      {!selectedTarget && (
        <p className={styles.validation}>
          왼쪽에서 연결 대상을 먼저 선택하면 “연결” 버튼이 활성화됩니다.
        </p>
      )}

      <h3 className={styles.sectionTitle}>기본 나레이션 보이스</h3>
      {narratorVoices.length === 0 ? (
        <p className={styles.empty}>기본 나레이션 보이스가 없습니다.</p>
      ) : (
        <ul className={styles.voiceList}>
          {narratorVoices.map((v) => (
            <VoiceCard key={v.voiceId} voice={v} />
          ))}
        </ul>
      )}

      <h3 className={styles.sectionTitle}>내 보이스 (캐릭터용)</h3>
      {characterVoices.length === 0 ? (
        <p className={styles.empty}>아직 생성한 보이스가 없습니다. 아래에서 만들어보세요.</p>
      ) : (
        <ul className={styles.voiceList}>
          {characterVoices.map((v) => (
            <VoiceCard key={v.voiceId} voice={v} />
          ))}
        </ul>
      )}

      <h3 className={styles.sectionTitle}>보이스 생성</h3>
      <VoiceCreateForm />
    </div>
  )
}

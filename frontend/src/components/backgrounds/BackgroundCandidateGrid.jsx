import useBackgroundStore from '@/store/useBackgroundStore'
import BackgroundCandidateCard from './BackgroundCandidateCard'
import styles from '@/pages/background/BackgroundPage.module.css'

export default function BackgroundCandidateGrid() {
  const candidates = useBackgroundStore((s) => s.candidates)

  if (candidates.length === 0) {
    return <p className={styles.empty}>아직 생성된 후보가 없어요. 프롬프트를 입력하고 후보를 생성해보세요.</p>
  }

  return (
    <ul className={styles.grid}>
      {candidates.map((c) => (
        <BackgroundCandidateCard key={c.candidateId} candidate={c} />
      ))}
    </ul>
  )
}

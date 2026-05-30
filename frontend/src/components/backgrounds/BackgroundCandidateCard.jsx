import useBackgroundStore from '@/store/useBackgroundStore'
import styles from '@/pages/background/BackgroundPage.module.css'

// 후보는 저장 전 임시 데이터이므로 삭제 버튼이 없다. 클릭하면 선택만 한다.
export default function BackgroundCandidateCard({ candidate }) {
  const selectedCandidateId = useBackgroundStore((s) => s.selectedCandidateId)
  const setSelectedCandidateId = useBackgroundStore((s) => s.setSelectedCandidateId)

  const isSelected = candidate.candidateId === selectedCandidateId

  return (
    <li
      className={`${styles.card} ${isSelected ? styles.cardSelected : ''}`}
      onClick={() => setSelectedCandidateId(candidate.candidateId)}
    >
      <div className={styles.thumb}>
        {candidate.imageUrl ? (
          <img src={candidate.imageUrl} alt={candidate.candidateId} className={styles.thumbImg} />
        ) : (
          <span className={styles.thumbEmpty}>이미지 준비 중</span>
        )}
      </div>
      <span className={styles.cardMeta}>{candidate.candidateId}</span>
      {isSelected && <span className={styles.selectedBadge}>선택됨</span>}
    </li>
  )
}

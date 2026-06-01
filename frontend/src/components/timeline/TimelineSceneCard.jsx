import styles from './Timeline.module.css'
import SceneComposite from './SceneComposite'

// readyStatus 뱃지(배경/캐릭터/텍스트). 있으면 ✅, 없으면 ⚠ 경고 스타일.
function StatusBadges({ readyStatus }) {
  const items = [
    ['배경', readyStatus?.hasBackground],
    ['캐릭터', readyStatus?.hasCharacters],
    ['텍스트', readyStatus?.hasText],
  ]
  return (
    <div className={styles.badges}>
      {items.map(([label, ok]) => (
        <span key={label} className={`${styles.badge}${ok ? '' : ` ${styles.badgeWarn}`}`}>
          {label} {ok ? '✅' : '⚠'}
        </span>
      ))}
    </div>
  )
}

// 씬 카드. 순서는 스토리 원본 고정(재배치 없음). 클릭하면 상세 패널에서 선택.
export default function TimelineSceneCard({ scene, selected, onSelect }) {
  const chars = scene.characters ?? []

  return (
    <div
      className={`${styles.card}${selected ? ` ${styles.cardSelected}` : ''}`}
      onClick={() => onSelect(scene.sceneId)}
    >
      <div className={styles.cardHead}>
        <span className={styles.cardOrder}>씬 {scene.order}</span>
      </div>

      {/* 배경 + 캐릭터(layout)까지 합성된 씬 미리보기 — scene-editor 배치를 그대로 재현 */}
      <SceneComposite
        className={styles.thumb}
        backgroundUrl={scene.background?.imageUrl}
        characters={chars}
      />

      <span className={styles.charLine}>
        {chars.length > 0 ? chars.map((c) => c.name).join(', ') : '캐릭터 없음'}
      </span>
      <p className={styles.textPreview}>{scene.textPreview || '텍스트 없음'}</p>
      <span className={styles.cardDuration}>{(scene.duration ?? 3).toFixed(1)}초</span>
      <StatusBadges readyStatus={scene.readyStatus} />
    </div>
  )
}

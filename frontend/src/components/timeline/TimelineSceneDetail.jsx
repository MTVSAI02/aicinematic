import styles from './Timeline.module.css'
import DurationControl from './DurationControl'
import SceneComposite from './SceneComposite'

// 선택한 씬 상세 패널: 배경 썸네일 / 텍스트 / duration 조절 / readyStatus / 캐릭터 목록.
export default function TimelineSceneDetail({ scene, onDurationChange }) {
  if (!scene) {
    return <div className={styles.detail}><span className={styles.empty}>씬을 선택하세요.</span></div>
  }
  const chars = scene.characters ?? []
  const rs = scene.readyStatus ?? {}
  const statusLine = [
    ['배경', rs.hasBackground],
    ['캐릭터', rs.hasCharacters],
    ['텍스트', rs.hasText],
  ]

  return (
    <div className={styles.detail}>
      <SceneComposite
        className={styles.detailThumb}
        backgroundUrl={scene.background?.imageUrl}
        characters={chars}
      />

      <div className={styles.detailBody}>
        <div className={styles.detailTitle}>씬 {scene.order}</div>
        <p className={styles.detailText}>{scene.textPreview || '텍스트 없음'}</p>

        <div>
          <div className={styles.detailTitle} style={{ marginBottom: 6 }}>재생 길이</div>
          <DurationControl duration={scene.duration} onChange={(d) => onDurationChange(scene.sceneId, d)} />
        </div>

        <div className={styles.badges}>
          {statusLine.map(([label, ok]) => (
            <span key={label} className={`${styles.badge}${ok ? '' : ` ${styles.badgeWarn}`}`}>
              {label} {ok ? '✅' : '없음 ⚠'}
            </span>
          ))}
        </div>

        {chars.length > 0 && (
          <div className={styles.detailChars}>
            {chars.map((c) => (
              <span key={c.characterId} className={styles.chip}>
                {c.imageUrl && <img className={styles.chipAvatar} src={c.imageUrl} alt="" draggable={false} />}
                {c.name}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

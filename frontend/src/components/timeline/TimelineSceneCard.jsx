import styles from './Timeline.module.css'
import SceneComposite from './SceneComposite'

// 음성은 3단계(ready/generating/failed/none)로 표시. 나머지는 ✅/⚠.
const AUDIO_BADGE = {
  ready: ['음성 ✅', false],
  generating: ['음성 ⏳ 생성 중', false],
  failed: ['음성 ⚠ 실패', true],
  none: ['음성 ⚠', true],
}

function StatusBadges({ readyStatus }) {
  const items = [
    ['배경', readyStatus?.hasBackground],
    ['캐릭터', readyStatus?.hasCharacters],
    ['텍스트', readyStatus?.hasText],
  ]
  const [audioText, audioWarn] = AUDIO_BADGE[readyStatus?.audioStatus] ?? AUDIO_BADGE.none
  return (
    <div className={styles.badges}>
      {items.map(([label, ok]) => (
        <span key={label} className={`${styles.badge}${ok ? '' : ` ${styles.badgeWarn}`}`}>
          {label} {ok ? '✅' : '⚠'}
        </span>
      ))}
      <span className={`${styles.badge}${audioWarn ? ` ${styles.badgeWarn}` : ''}`}>{audioText}</span>
    </div>
  )
}

// 씬 카드. 순서는 스토리 원본 고정(재배치 없음). 클릭하면 상세 패널에서 선택.
// playing: 전체 미리보기 재생 중 현재 씬이면 표시.
export default function TimelineSceneCard({ scene, selected, playing, onSelect }) {
  const chars = scene.characters ?? []
  // 요약: 첫 cue label + 첫 item 텍스트(없으면 textPreview fallback). 카드는 선택용 요약만.
  const firstCue = [...(scene.cueTimings ?? [])].sort((a, b) => a.cueOrder - b.cueOrder)[0]
  const cueLabel = firstCue ? `씬 ${scene.order}-${firstCue.cueOrder}` : null
  const summaryText = firstCue?.items?.[0]?.text || scene.textPreview || '텍스트 없음'

  return (
    <div
      className={`${styles.card}${selected ? ` ${styles.cardSelected}` : ''}${playing ? ` ${styles.cardPlaying}` : ''}`}
      onClick={() => onSelect(scene.sceneId)}
    >
      <div className={styles.cardHead}>
        <span className={styles.cardOrder}>씬 {scene.order}</span>
        {playing && <span className={styles.cardPlayingTag}>▶ 재생 중</span>}
      </div>

      {/* 배경 + 캐릭터만 합성(자막 오버레이는 카드에선 생략 — 겹침 방지). 전체 자막은 상세에서. */}
      <SceneComposite
        className={styles.thumb}
        backgroundUrl={scene.background?.imageUrl}
        characters={chars}
        textOverlays={[]}
      />

      <p className={styles.cardSummary}>
        {cueLabel && <span className={styles.cardCueLabel}>{cueLabel} · </span>}
        {summaryText}
      </p>

      <div className={styles.cardFoot}>
        <span className={styles.cardDuration}>{(scene.duration ?? 3).toFixed(1)}초</span>
        <StatusBadges readyStatus={scene.readyStatus} />
      </div>
    </div>
  )
}

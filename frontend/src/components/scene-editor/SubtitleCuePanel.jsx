import styles from '@/pages/scene-editor/SceneEditorPage.module.css'

// cue 그룹 안 개별 자막 보조번호(①②③…)
const circled = (i) => '①②③④⑤⑥⑦⑧⑨⑩'[i] ?? `#${i + 1}`

// 씬 편집의 자막 패널. 자막은 대본에서 자동 생성(읽기전용)이고, 여기선 cue 그룹 배정/선택만 한다.
// 위치/크기/회전은 스테이지에서, 텍스트 추가/수정은 없음.
export default function SubtitleCuePanel({
  sceneOrder,
  overlays,
  cueSlots,
  selected,
  editMode,
  activeCue,
  onEnterCue,
  onSelectOverlay,
  onSetCueGroup,
}) {
  // cue 그룹별로 묶기: [[cueOrder, overlays[]], ...] (cueOrder 오름차순)
  const cueGroups = (() => {
    const m = new Map()
    for (const o of overlays) {
      if (!m.has(o.cueOrder)) m.set(o.cueOrder, [])
      m.get(o.cueOrder).push(o)
    }
    return [...m.entries()].sort((a, b) => a[0] - b[0])
  })()

  return (
    <div className={styles.bgPanel}>
      <span className={styles.panelLabel}>자막 (cue 그룹 · 배치)</span>
      <span className={styles.muted}>
        자막은 대본에서 자동 생성됩니다(텍스트 읽기전용). 스테이지에서 <b>위치·크기·회전</b>을 조절하고, 아래에서{' '}
        <b>cue 그룹</b>(씬 {sceneOrder}-N)을 정하세요. 같은 cue = 같은 타이밍에 함께 등장.
      </span>

      {overlays.length === 0 ? (
        <span className={styles.muted}>이 씬에 자막으로 쓸 텍스트가 없습니다.</span>
      ) : (
        cueGroups.map(([cue, items]) => (
          <div
            key={cue}
            className={`${styles.cueGroup} ${editMode === 'subtitle' && activeCue === cue ? styles.cueGroupActive : ''}`}
          >
            <button
              className={styles.cueGroupHead}
              onClick={() => onEnterCue(cue)}
              title="이 cue 그룹 편집(스테이지에 이 자막들만 표시)"
            >
              <span className={styles.subtitleLabel}>씬 {sceneOrder}-{cue}</span>
              <span className={styles.muted}>
                {items.length}개 자막{editMode === 'subtitle' && activeCue === cue ? ' · 편집 중' : ''}
              </span>
            </button>
            {items.map((o, j) => {
              const isSel = selected?.kind === 'text' && selected.id === o.textOverlayId
              return (
                <div key={o.textOverlayId} className={styles.subtitleRow}>
                  <button
                    className={`${styles.subtitleUnit} ${isSel ? styles.subtitleUnitSel : ''}`}
                    onClick={() => {
                      onEnterCue(o.cueOrder)
                      onSelectOverlay(o.textOverlayId)
                    }}
                  >
                    <span className={styles.muted}>
                      {circled(j)} {o.speaker ? `${o.speaker} · ` : ''}
                      {o.text}
                      {isSel ? ' (선택됨)' : ''}
                    </span>
                  </button>
                  <label className={styles.cuePick}>
                    cue
                    <select
                      className={styles.cueSelect}
                      value={o.cueOrder}
                      onChange={(e) => onSetCueGroup(o.textOverlayId, Number(e.target.value))}
                      title="이 자막을 넣을 cue 그룹"
                    >
                      {cueSlots.map((n) => (
                        <option key={n} value={n}>
                          {sceneOrder}-{n}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              )
            })}
          </div>
        ))
      )}
    </div>
  )
}

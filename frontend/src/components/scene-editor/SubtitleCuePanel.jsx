import styles from '@/pages/scene-editor/SceneEditorPage.module.css'
import navSlateIcon from '@design/assets/figma-icons/Nav/nav_scene_editor.svg'

// cue 그룹 안 개별 자막 보조번호(①②③…)
const circled = (i) => '①②③④⑤⑥⑦⑧⑨⑩'[i] ?? `#${i + 1}`

// 1차 자막 스타일: 정렬(cue 단위 3종) + 글자색(씬 단위 팔레트, 직접 hex 입력 없음).
const ALIGNS = [
  ['left', '왼쪽'],
  ['center', '가운데'],
  ['right', '오른쪽'],
]
// 배경 위 가독성 좋은 진한 대비색 6종
const PALETTE = [
  ['흰색', '#FFFFFF'],
  ['검정', '#111111'],
  ['남색', '#1E3A8A'],
  ['자주', '#BE123C'],
  ['갈색', '#92400E'],
  ['녹색', '#065F46'],
]
const DEFAULT_COLOR = '#111111'

// 씬 단위 자막 배경(투명/검정30%/흰색30%) — 옵션값은 백엔드와 동일.
const BACKGROUNDS = [
  ['none', '없음'],
  ['black', '검정'],
  ['white', '흰색'],
]

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
  onSetCueAlign,
  sceneTextColor,
  onSetSceneColor,
  subtitleBackground = 'none',
  onSetSceneBackground,
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

  const curSceneColor = (sceneTextColor || DEFAULT_COLOR).toUpperCase()

  return (
    <div className={styles.bgPanel}>
      <div className={styles.panelHeader}>
        <img src={navSlateIcon} alt="" className={styles.panelIcon} />
        <span className={styles.panelLabel}>자막 / cue 편집</span>
      </div>

      <div className={styles.panelBody}>
        {/* 씬 단위 글자색 */}
        {overlays.length > 0 && (
          <div className={styles.colorSection}>
            <span className={styles.panelSubLabel}>자막 색상</span>
            <div className={styles.colorPalette}>
              {PALETTE.map(([label, hex]) => {
                const sel = curSceneColor === hex.toUpperCase()
                return (
                  <button
                    key={hex}
                    type="button"
                    title={label}
                    aria-label={label}
                    onClick={() => onSetSceneColor(hex)}
                    className={`${styles.colorChip}${sel ? ` ${styles.colorChipSelected}` : ''}`}
                    style={{ background: hex }}
                  />
                )
              })}
            </div>
          </div>
        )}

        {/* 씬 단위 자막 배경(없음/검정/흰색) */}
        {overlays.length > 0 && (
          <div className={styles.colorSection}>
            <span className={styles.panelSubLabel}>자막 배경</span>
            <div className={styles.alignBtns}>
              {BACKGROUNDS.map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => onSetSceneBackground(value)}
                  className={`${styles.alignBtn}${subtitleBackground === value ? ` ${styles.alignBtnActive}` : ''}`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        )}

        {overlays.length === 0 ? (
          <span className={styles.muted}>이 씬에 자막으로 쓸 텍스트가 없습니다.</span>
        ) : (
          <div className={styles.cueGroupsContainer}>
            {cueGroups.map(([cue, items]) => {
              const curAlign = items[0]?.layout?.align ?? 'center'
              const isEditingGroup = editMode === 'subtitle' && activeCue === cue
              return (
                <div
                  key={cue}
                  className={`${styles.cueGroup} ${isEditingGroup ? styles.cueGroupActive : ''}`}
                >
                  <button
                    type="button"
                    className={styles.cueGroupHead}
                    onClick={() => onEnterCue(cue)}
                    title="이 cue 그룹 편집"
                  >
                    <span className={styles.subtitleLabel}>씬 {sceneOrder}-{cue}</span>
                    <span className={styles.muted}>
                      {items.length}개 자막{isEditingGroup ? ' · 편집 중' : ''}
                    </span>
                  </button>

                  {/* 정렬 버튼 */}
                  <div className={styles.alignGroupRow}>
                    <span className={styles.mutedSmall}>정렬</span>
                    <div className={styles.alignBtns}>
                      {ALIGNS.map(([v, label]) => (
                        <button
                          key={v}
                          type="button"
                          onClick={() => onSetCueAlign(cue, v)}
                          className={`${styles.alignBtn}${curAlign === v ? ` ${styles.alignBtnActive}` : ''}`}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* 개별 대사들 */}
                  <div className={styles.cueItemsList}>
                    {items.map((o, j) => {
                      const isSel = selected?.kind === 'text' && selected.id === o.textOverlayId
                      return (
                        <div key={o.textOverlayId} className={styles.subtitleRow}>
                          <button
                            type="button"
                            className={`${styles.subtitleUnit} ${isSel ? styles.subtitleUnitSel : ''}`}
                            onClick={() => {
                              onEnterCue(o.cueOrder)
                              onSelectOverlay(o.textOverlayId)
                            }}
                          >
                            <span className={styles.subtitleRowText}>
                              {circled(j)} {o.speaker ? `${o.speaker} · ` : ''}
                              {o.text}
                            </span>
                          </button>
                          <label className={styles.cuePick}>
                            <span className={styles.cueLabelText}>cue</span>
                            <select
                              className={styles.cueSelect}
                              value={o.cueOrder}
                              onChange={(e) => onSetCueGroup(o.textOverlayId, Number(e.target.value))}
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
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

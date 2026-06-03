import styles from '@/pages/scene-editor/SceneEditorPage.module.css'

// cue 그룹 안 개별 자막 보조번호(①②③…)
const circled = (i) => '①②③④⑤⑥⑦⑧⑨⑩'[i] ?? `#${i + 1}`

// 1차 자막 스타일: 정렬(cue 단위 3종) + 글자색(씬 단위 팔레트, 직접 hex 입력 없음).
const ALIGNS = [
  ['left', '왼쪽'],
  ['center', '가운데'],
  ['right', '오른쪽'],
]
// 배경 위 가독성 좋은 진한 대비색 5종(밝은 파스텔 제외).
const PALETTE = [
  ['흰색', '#FFFFFF'],
  ['검정', '#111111'],
  ['남색', '#1E3A8A'],
  ['자주', '#BE123C'],
  ['갈색', '#92400E'],
]
const DEFAULT_COLOR = '#111111'

// 씬 편집의 자막 패널. 자막은 대본에서 자동 생성(읽기전용).
// 글자색은 씬 단위(상단 1회), 정렬은 cue 단위. 위치/크기/회전은 스테이지에서.
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
      <span className={styles.panelLabel}>자막 (cue 그룹 · 정렬 · 색상)</span>
      <span className={styles.muted}>
        자막은 대본에서 자동 생성됩니다(텍스트 읽기전용). 스테이지에서 <b>위치·크기·회전</b>을, 아래에서{' '}
        <b>cue 그룹</b>·<b>정렬</b>을 정하세요. <b>글자색은 씬 전체에 한 번</b> 적용됩니다.
      </span>

      {/* 씬 단위 글자색 (패널 상단 1회) */}
      {overlays.length > 0 && (
        <div style={{ margin: '10px 0 4px' }}>
          <div className={styles.subtitleLabel}>씬 자막 색상</div>
          <div className={styles.muted} style={{ margin: '2px 0 6px' }}>이 씬의 모든 자막에 적용됩니다.</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center' }}>
            {PALETTE.map(([label, hex]) => {
              const sel = curSceneColor === hex.toUpperCase()
              return (
                <button
                  key={hex}
                  type="button"
                  title={label}
                  aria-label={label}
                  onClick={() => onSetSceneColor(hex)}
                  style={{
                    width: 22,
                    height: 22,
                    borderRadius: '50%',
                    cursor: 'pointer',
                    background: hex,
                    border: sel ? '2px solid var(--accent)' : '1px solid var(--border)',
                    boxShadow: sel ? '0 0 0 2px var(--accent-bg)' : 'none',
                  }}
                />
              )
            })}
          </div>
        </div>
      )}

      {overlays.length === 0 ? (
        <span className={styles.muted}>이 씬에 자막으로 쓸 텍스트가 없습니다.</span>
      ) : (
        cueGroups.map(([cue, items]) => {
          const curAlign = items[0]?.layout?.align ?? 'center'
          return (
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

              {/* cue 단위 정렬 (그 cue 모든 item 에 동일 적용) */}
              <div style={{ display: 'flex', gap: 4, alignItems: 'center', margin: '6px 0 8px' }}>
                <span className={styles.muted}>정렬</span>
                {ALIGNS.map(([v, label]) => (
                  <button
                    key={v}
                    type="button"
                    onClick={() => onSetCueAlign(cue, v)}
                    style={{
                      fontSize: 12,
                      padding: '3px 8px',
                      borderRadius: 6,
                      cursor: 'pointer',
                      background: curAlign === v ? 'var(--accent-bg)' : 'var(--bg)',
                      border: `1px solid ${curAlign === v ? 'var(--accent)' : 'var(--border)'}`,
                      color: curAlign === v ? 'var(--accent)' : 'var(--text)',
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>

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
                      <span
                        className={styles.muted}
                        style={{
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical',
                          overflow: 'hidden',
                          textAlign: 'left',
                        }}
                      >
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
          )
        })
      )}
    </div>
  )
}

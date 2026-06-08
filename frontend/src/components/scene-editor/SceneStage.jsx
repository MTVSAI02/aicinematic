import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import Moveable from 'react-moveable'
import { mediaUrl } from '@/utils/mediaUrl'
import styles from './SceneStage.module.css'

// 씬 합성 미리보기 + 배치 편집 (react-moveable).
// 레이어: 배경 → 캐릭터(img) → 자막(div). 캐릭터/자막을 하나의 선택 모델로 다룬다.
//   selected = { kind: 'character' | 'text', id } | null  (페이지에서 관리)
// layout 은 모두 정규화 좌표(미리보기/타임라인/2차 렌더 해상도 무관):
//   - 캐릭터: x/y=중심, scale=너비 비율, rotation, zIndex, flipX
//   - 자막:   x/y=중심, width=박스 폭 비율, fontSize=글자 크기(높이 대비), rotation, zIndex, align
// 위치는 transform translate(px) 로만 관리(= Moveable 표현과 동일) → 점프 없음.
// 1차 자막 리사이즈는 "글자 크기 스케일"(A안): 박스 폭과 fontSize 를 같은 비율로 키운다.

const DEFAULT_CHAR_LAYOUT = { x: 0.5, y: 0.55, scale: 0.28, rotation: 0, zIndex: 1, flipX: false }
export const DEFAULT_TEXT_LAYOUT = {
  x: 0.5, y: 0.86, width: 0.75, fontSize: 0.06, rotation: 0, zIndex: 100, align: 'center',
}
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v))

export default function SceneStage({
  backgroundUrl,
  characters,
  textOverlays = [],
  selected,
  onSelect,
  onCharacterLayoutChange,
  onTextOverlayLayoutChange,
  editMode = 'character', // 'character' | 'subtitle'
  activeCue = null, // 자막 모드에서 보여줄 cue 그룹 번호
}) {
  const charMode = editMode === 'character'
  // 자막 모드에선 active cue 자막만 보인다. 캐릭터 모드에선 자막 숨김.
  const visibleOverlays = charMode ? [] : textOverlays.filter((o) => o.cueOrder === activeCue)
  const stageRef = useRef(null)
  const [stage, setStage] = useState({ w: 0, h: 0 })
  const [bgAspect, setBgAspect] = useState(16 / 9)
  const [aspects, setAspects] = useState({}) // characterId -> naturalW/naturalH
  const [textHeights, setTextHeights] = useState({}) // textOverlayId -> 측정된 px 높이(자동 높이 중심정렬용)
  const targetRefs = useRef({}) // `${kind}:${id}` -> DOM element
  // 조작 중 누적 상태(렌더 없이 ref). translate = 박스 좌상단(스테이지 좌표, 절대).
  const frame = useRef({ translate: [0, 0], rotate: 0, width: 0, height: 0, baseWidth: 0, baseFont: 0 })

  useEffect(() => {
    const el = stageRef.current
    if (!el) return
    const update = () => setStage({ w: el.clientWidth, h: el.clientHeight })
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  // 선택된 요소가 목록에서 사라지면 선택 해제 → detached DOM 을 Moveable 이 잡지 않게.
  useEffect(() => {
    if (!selected) return
    const exists =
      selected.kind === 'character'
        ? characters.some((c) => c.characterId === selected.id)
        : textOverlays.some((o) => o.textOverlayId === selected.id)
    if (!exists) onSelect(null)
  }, [characters, textOverlays, selected, onSelect])

  // 자막 div 는 높이가 내용에 따라 자동이라, 중심정렬(ty) 계산용으로 실제 높이를 측정해 둔다.
  useLayoutEffect(() => {
    if (stage.w === 0) return
    let changed = false
    const next = {}
    for (const o of visibleOverlays) {
      const el = targetRefs.current[`text:${o.textOverlayId}`]
      if (el) {
        const h = el.offsetHeight
        next[o.textOverlayId] = h
        if (Math.abs((textHeights[o.textOverlayId] || 0) - h) > 0.5) changed = true
      }
    }
    if (changed || Object.keys(next).length !== Object.keys(textHeights).length) setTextHeights(next)
  })

  // ── 기하 (정규화 layout → px) ─────────────────────────────
  function charGeom(c) {
    const layout = { ...DEFAULT_CHAR_LAYOUT, ...(c.layout || {}) }
    const aspect = aspects[c.characterId]
    const width = clamp(layout.scale, 0.05, 1) * stage.w
    const height = aspect ? width / aspect : width
    return { layout, width, height, tx: layout.x * stage.w - width / 2, ty: layout.y * stage.h - height / 2 }
  }
  function textGeom(o) {
    const layout = { ...DEFAULT_TEXT_LAYOUT, ...(o.layout || {}) }
    const width = clamp(layout.width, 0.1, 1) * stage.w
    const fontSize = clamp(layout.fontSize, 0.01, 0.2) * stage.h
    const height = textHeights[o.textOverlayId] ?? fontSize * 1.6
    return { layout, width, fontSize, height, tx: layout.x * stage.w - width / 2, ty: layout.y * stage.h - height / 2 }
  }

  const selKey = selected ? `${selected.kind}:${selected.id}` : null
  // 현재 모드와 맞는 선택만 활성(캐릭터는 캐릭터 모드, 자막은 자막 모드에서만)
  const modeMatches = selected && (selected.kind === 'character') === charMode
  const selectedTarget = modeMatches && selKey ? targetRefs.current[selKey] : null
  const isTextSel = selected?.kind === 'text' && !charMode

  // 스냅 가이드: 선택 외 다른 요소들과 정렬 맞춤
  const otherTargets = selected
    ? Object.entries(targetRefs.current)
        .filter(([k, el]) => el && k !== selKey)
        .map(([, el]) => el)
    : []

  function startFrame() {
    if (!selected) return
    if (selected.kind === 'character') {
      const c = characters.find((x) => x.characterId === selected.id)
      if (!c) return
      const g = charGeom(c)
      frame.current = { translate: [g.tx, g.ty], rotate: g.layout.rotation || 0, width: g.width, height: g.height, baseWidth: g.width, baseFont: 0 }
    } else {
      const o = textOverlays.find((x) => x.textOverlayId === selected.id)
      if (!o) return
      const g = textGeom(o)
      // mode: 'scale'(코너=글자+폭 비례) | 'width'(좌우 변=폭만, 글자 고정 → 자동 줄바꿈)
      frame.current = { translate: [g.tx, g.ty], rotate: g.layout.rotation || 0, width: g.width, height: g.height, baseWidth: g.width, baseFont: g.fontSize, mode: 'scale' }
    }
  }

  function applyTransform(target) {
    const f = frame.current
    target.style.transform = `translate(${f.translate[0]}px, ${f.translate[1]}px) rotate(${f.rotate}deg)`
  }

  function commit() {
    if (!selected) return
    const f = frame.current
    const centerX = f.translate[0] + f.width / 2
    const centerY = f.translate[1] + f.height / 2
    if (selected.kind === 'character') {
      const c = characters.find((x) => x.characterId === selected.id)
      if (!c) return
      const layout = { ...DEFAULT_CHAR_LAYOUT, ...(c.layout || {}) }
      onCharacterLayoutChange(selected.id, {
        ...layout,
        x: clamp(centerX / stage.w, 0, 1),
        y: clamp(centerY / stage.h, 0, 1),
        scale: clamp(f.width / stage.w, 0.05, 1),
        rotation: f.rotate,
      })
    } else {
      const o = textOverlays.find((x) => x.textOverlayId === selected.id)
      if (!o) return
      const layout = { ...DEFAULT_TEXT_LAYOUT, ...(o.layout || {}) }
      // ratio = 현재폭 / 시작폭. 코너(scale)는 글자도 같이, 좌우 변(width)은 글자 고정(자동 줄바꿈).
      const ratio = f.baseWidth > 0 ? f.width / f.baseWidth : 1
      onTextOverlayLayoutChange(selected.id, {
        ...layout,
        x: clamp(centerX / stage.w, 0, 1),
        y: clamp(centerY / stage.h, 0, 1),
        width: clamp(layout.width * ratio, 0.1, 1),
        fontSize: f.mode === 'width' ? layout.fontSize : clamp(layout.fontSize * ratio, 0.01, 0.2),
        rotation: f.rotate,
      })
    }
  }

  return (
    <div
      ref={stageRef}
      className={styles.stage}
      style={{ aspectRatio: String(bgAspect) }}
      onPointerDown={(e) => {
        if (e.target === stageRef.current || e.target.dataset?.bg) onSelect(null)
      }}
    >
      {backgroundUrl ? (
        <img
          src={mediaUrl(backgroundUrl)}
          alt=""
          data-bg="1"
          draggable={false}
          className={styles.bg}
          onLoad={(e) => setBgAspect(e.currentTarget.naturalWidth / e.currentTarget.naturalHeight)}
        />
      ) : (
        <div className={styles.placeholder}>배경을 연결하면 합성 미리보기가 표시됩니다</div>
      )}

      {/* 캐릭터 레이어 (이미지 대신 보라색 점선 박스 플레이스홀더로 렌더링) */}
      {stage.w > 0 &&
        characters.map((c) => {
          const g = charGeom(c)
          const isSel = selected?.kind === 'character' && selected.id === c.characterId
          return (
            <div
              key={`char:${c.characterId}`}
              ref={(el) => {
                if (el) targetRefs.current[`character:${c.characterId}`] = el
                else delete targetRefs.current[`character:${c.characterId}`]
              }}
              onPointerDown={charMode ? () => onSelect({ kind: 'character', id: c.characterId }) : undefined}
              className={`${styles.char}${charMode && !isSel ? ` ${styles.charUnselected}` : ''}`}
              style={{
                width: g.width,
                height: g.height,
                zIndex: g.layout.zIndex,
                transform: `translate(${g.tx}px, ${g.ty}px) rotate(${g.layout.rotation || 0}deg)`,
                // 자막 모드: 캐릭터는 참고용으로만 보이고 선택/이동 잠금
                pointerEvents: charMode ? 'auto' : 'none',
              }}
            >
              {c.imageUrl ? (
                <img
                  src={mediaUrl(c.imageUrl)}
                  alt={c.name}
                  className={styles.charImg}
                  style={{ transform: g.layout.flipX ? 'scaleX(-1)' : 'none' }}
                  onLoad={(e) => {
                    const { naturalWidth, naturalHeight } = e.currentTarget
                    setAspects((prev) => ({
                      ...prev,
                      [c.characterId]: naturalWidth / naturalHeight,
                    }))
                  }}
                  draggable={false}
                />
              ) : (
                <div
                  className={styles.charPlaceholder}
                  style={{ transform: g.layout.flipX ? 'scaleX(-1)' : 'none' }}
                >
                  <span className={styles.charPlaceholderName}>{c.name || '캐릭터'}</span>
                </div>
              )}
            </div>
          )
        })}

      {/* 자막 레이어 — 자막 모드에서 active cue 자막만 */}
      {stage.w > 0 &&
        visibleOverlays.map((o) => {
          const g = textGeom(o)
          const isSel = selected?.kind === 'text' && selected.id === o.textOverlayId
          const st = o.style || {}
          return (
            <div
              key={`text:${o.textOverlayId}`}
              ref={(el) => {
                if (el) targetRefs.current[`text:${o.textOverlayId}`] = el
                else delete targetRefs.current[`text:${o.textOverlayId}`]
              }}
              onPointerDown={() => onSelect({ kind: 'text', id: o.textOverlayId })}
              className={`${styles.textOverlay}${isSel ? ` ${styles.textOverlaySelected}` : ''}`}
              style={{
                width: g.width,
                zIndex: g.layout.zIndex,
                transform: `translate(${g.tx}px, ${g.ty}px) rotate(${g.layout.rotation || 0}deg)`,
                fontSize: g.fontSize,
                textAlign: g.layout.align,
                color: st.color || '#111111',
                background: st.backgroundColor || 'transparent', // 자막 배경 박스(none=투명, 렌더와 동일)
                borderRadius: `${(st.borderRadius ?? 0.02) * stage.h}px`, // 둥근 박스(렌더와 동일)
                fontFamily: "'Hakgyoansim Dunggeunmiso', sans-serif", // 자막 전용 폰트(Regular)
                fontWeight: 400, // Regular 만 사용(굵게 X)
                padding: `${(st.padding ?? 0.02) * stage.h}px`, // 박스 안쪽 여백(렌더와 동일, 투명일 땐 hit 영역)
              }}
            >
              {o.text}
            </div>
          )
        })}

      {selectedTarget && (
        <Moveable
          target={selectedTarget}
          rootContainer={typeof document !== 'undefined' ? document.body : undefined}
          draggable
          resizable
          rotatable
          keepRatio={!isTextSel}
          renderDirections={isTextSel ? ['nw', 'ne', 'sw', 'se', 'e', 'w'] : undefined}
          throttleDrag={0}
          throttleResize={0}
          throttleRotate={0}
          snappable
          snapContainer={stageRef.current}
          snapThreshold={7}
          verticalGuidelines={[stage.w * 0.5]}
          horizontalGuidelines={[stage.h * 0.5, stage.h * 0.9]}
          elementGuidelines={otherTargets}
          snapDirections={{ center: true, middle: true, top: true, bottom: true, left: true, right: true }}
          elementSnapDirections={{ center: true, middle: true, top: true, bottom: true, left: true, right: true }}
          snapRotationThreshold={5}
          snapRotationDegrees={[0, 45, 90, 135, 180, 225, 270, 315]}
          onDragStart={startFrame}
          onResizeStart={startFrame}
          onRotateStart={startFrame}
          onDrag={({ target, beforeTranslate }) => {
            frame.current.translate = beforeTranslate
            applyTransform(target)
          }}
          onResize={({ target, width, height, drag, direction }) => {
            frame.current.width = width
            frame.current.translate = drag.beforeTranslate
            if (isTextSel) {
              // 좌우 변(x만 변하는 핸들) → 폭만(글자 고정, 자동 줄바꿈). 코너 → 글자+폭 비례 스케일.
              const isSide = direction[0] !== 0 && direction[1] === 0
              frame.current.mode = isSide ? 'width' : 'scale'
              target.style.width = `${width}px`
              if (!isSide) {
                const ratio = frame.current.baseWidth > 0 ? width / frame.current.baseWidth : 1
                target.style.fontSize = `${frame.current.baseFont * ratio}px`
              }
              frame.current.height = target.offsetHeight // 줄바꿈 후 실제 높이(중심정렬용)
            } else {
              frame.current.height = height
              target.style.width = `${width}px`
              target.style.height = `${height}px`
            }
            applyTransform(target)
          }}
          onRotate={({ target, beforeRotate }) => {
            frame.current.rotate = beforeRotate
            applyTransform(target)
          }}
          onDragEnd={commit}
          onResizeEnd={commit}
          onRotateEnd={commit}
        />
      )}
    </div>
  )
}

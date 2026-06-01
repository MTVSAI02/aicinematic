import { useEffect, useRef, useState } from 'react'
import Moveable from 'react-moveable'
import styles from './SceneStage.module.css'

// 씬 합성 미리보기 + 캐릭터 배치 (react-moveable, PC 웹 단일 캐릭터 편집 기준).
// - 배경 위에 연결된 캐릭터(투명 PNG)를 올리고, 클릭 선택 → 이동/리사이즈/회전 + 스냅.
// - layout 은 정규화 좌표: x/y=중심(0~1), scale=스테이지 너비 대비 너비 비율, rotation=각도(도), flipX=좌우반전.
// - 위치는 transform translate 로만 관리(= Moveable 표현과 동일) → 렌더/Moveable 상태 일치, 점프 없음.
// - 드래그/리사이즈/회전 종료 시 onLayoutChange 로 저장 → 새로고침 후 복원.

const DEFAULT_LAYOUT = { x: 0.5, y: 0.55, scale: 0.28, rotation: 0, zIndex: 1, flipX: false }
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v))

export default function SceneStage({ backgroundUrl, characters, onLayoutChange }) {
  const stageRef = useRef(null)
  const [stage, setStage] = useState({ w: 0, h: 0 })
  const [bgAspect, setBgAspect] = useState(16 / 9)
  const [aspects, setAspects] = useState({}) // characterId -> naturalW/naturalH
  const [selectedId, setSelectedId] = useState(null)
  const targetRefs = useRef({}) // characterId -> DOM element
  // 조작 중 누적 상태(렌더 없이 ref). translate = 박스 좌상단(스테이지 좌표, 절대).
  const frame = useRef({ translate: [0, 0], rotate: 0, width: 0, height: 0 })

  useEffect(() => {
    const el = stageRef.current
    if (!el) return
    const update = () => setStage({ w: el.clientWidth, h: el.clientHeight })
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  // 선택된 캐릭터가 목록에서 사라지면(제거 등) 선택 해제 → detached DOM 을 Moveable 이 잡지 않게.
  useEffect(() => {
    if (selectedId && !characters.some((c) => c.characterId === selectedId)) {
      setSelectedId(null)
    }
  }, [characters, selectedId])

  // layout(정규화) → px 기하. translate = 박스 좌상단(스테이지 좌표).
  function geomOf(c) {
    const layout = { ...DEFAULT_LAYOUT, ...(c.layout || {}) }
    const aspect = aspects[c.characterId]
    const width = clamp(layout.scale, 0.05, 1) * stage.w
    const height = aspect ? width / aspect : width
    const tx = layout.x * stage.w - width / 2
    const ty = layout.y * stage.h - height / 2
    return { layout, width, height, tx, ty }
  }

  const selectedChar = characters.find((c) => c.characterId === selectedId) || null
  const selectedTarget = selectedId ? targetRefs.current[selectedId] : null
  // 스냅 가이드: 선택된 캐릭터 외 나머지 캐릭터 요소(= 다른 캐릭터와 정렬 맞춤용)
  const otherTargets = selectedId
    ? characters
        .filter((c) => c.characterId !== selectedId)
        .map((c) => targetRefs.current[c.characterId])
        .filter(Boolean)
    : []

  function startFrame() {
    if (!selectedChar) return
    const g = geomOf(selectedChar)
    frame.current = {
      translate: [g.tx, g.ty],
      rotate: g.layout.rotation || 0,
      width: g.width,
      height: g.height,
    }
  }

  function applyTransform(target) {
    const f = frame.current
    target.style.transform = `translate(${f.translate[0]}px, ${f.translate[1]}px) rotate(${f.rotate}deg)`
  }

  // 종료 시: frame(절대 translate/크기/각도) → 정규화 layout 으로 변환해 저장.
  function commit() {
    if (!selectedChar) return
    const f = frame.current
    const centerX = f.translate[0] + f.width / 2
    const centerY = f.translate[1] + f.height / 2
    const layout = { ...DEFAULT_LAYOUT, ...(selectedChar.layout || {}) }
    onLayoutChange(selectedChar.characterId, {
      ...layout,
      x: clamp(centerX / stage.w, 0, 1),
      y: clamp(centerY / stage.h, 0, 1),
      scale: clamp(f.width / stage.w, 0.05, 1),
      rotation: f.rotate,
    })
  }

  return (
    <div
      ref={stageRef}
      className={styles.stage}
      style={{ aspectRatio: String(bgAspect) }}
      onPointerDown={(e) => {
        if (e.target === stageRef.current || e.target.dataset?.bg) setSelectedId(null)
      }}
    >
      {backgroundUrl ? (
        <img
          src={backgroundUrl}
          alt=""
          data-bg="1"
          draggable={false}
          className={styles.bg}
          onLoad={(e) => {
            const img = e.currentTarget
            setBgAspect(img.naturalWidth / img.naturalHeight)
          }}
        />
      ) : (
        <div className={styles.placeholder}>배경을 연결하면 합성 미리보기가 표시됩니다</div>
      )}

      {stage.w > 0 &&
        characters.map((c) => {
          const g = geomOf(c)
          const isSelected = c.characterId === selectedId
          return (
            <div
              key={c.characterId}
              ref={(el) => {
                // stale ref 방지: 마운트 시 등록, 언마운트(el===null) 시 제거
                if (el) targetRefs.current[c.characterId] = el
                else delete targetRefs.current[c.characterId]
              }}
              onPointerDown={() => setSelectedId(c.characterId)}
              className={`${styles.char}${isSelected ? '' : ` ${styles.charUnselected}`}`}
              style={{
                width: g.width,
                height: g.height,
                zIndex: g.layout.zIndex,
                transform: `translate(${g.tx}px, ${g.ty}px) rotate(${g.layout.rotation || 0}deg)`,
              }}
            >
              <img
                src={c.imageUrl}
                alt=""
                draggable={false}
                className={styles.charImg}
                onLoad={(e) => {
                  const img = e.currentTarget
                  const ratio = img.naturalWidth / img.naturalHeight
                  setAspects((prev) => ({ ...prev, [c.characterId]: ratio }))
                }}
                style={{ transform: g.layout.flipX ? 'scaleX(-1)' : 'none' }}
              />
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
          keepRatio
          throttleDrag={0}
          throttleResize={0}
          throttleRotate={0}
          // ── 2단계: 스냅/가이드 ─────────────────────────────
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
          onResize={({ target, width, height, drag }) => {
            frame.current.width = width
            frame.current.height = height
            frame.current.translate = drag.beforeTranslate
            target.style.width = `${width}px`
            target.style.height = `${height}px`
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

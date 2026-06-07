import { useEffect, useRef, useState } from 'react'

// 읽기전용 미니 합성: 배경 위에 캐릭터(layout) + 자막(textOverlays)을 정규화 좌표대로 겹쳐 보여준다.
// %(정규화) 좌표를 그대로 써서 카드 썸네일/상세 등 어떤 크기에서도 동일 배치로 스케일된다.
// (scene-editor SceneStage의 편집 버전과 같은 배치를 읽기전용으로 재현)

const DEFAULT_LAYOUT = { x: 0.5, y: 0.55, scale: 0.28, rotation: 0, zIndex: 1, flipX: false }
const DEFAULT_TEXT_LAYOUT = { x: 0.5, y: 0.86, width: 0.75, fontSize: 0.06, rotation: 0, zIndex: 100, align: 'center' }

export default function SceneComposite({
  backgroundUrl,
  characters = [],
  textOverlays = [],
  className,
  emptyText = '배경 없음',
}) {
  const ref = useRef(null)
  const [h, setH] = useState(0) // 자막 fontSize(정규화) → px 환산용 컨테이너 높이

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const update = () => setH(el.clientHeight)
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  return (
    <div ref={ref} className={className} style={{ position: 'relative', overflow: 'hidden' }}>
      {backgroundUrl ? (
        <img
          src={backgroundUrl}
          alt=""
          draggable={false}
          style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }}
        />
      ) : (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--text)',
            fontSize: 12,
          }}
        >
          {emptyText}
        </div>
      )}

      {characters.map((c) => {
        if (!c.imageUrl) return null
        const L = { ...DEFAULT_LAYOUT, ...(c.layout || {}) }
        return (
          <img
            key={c.characterId}
            src={c.imageUrl}
            alt=""
            draggable={false}
            style={{
              position: 'absolute',
              left: `${L.x * 100}%`,
              top: `${L.y * 100}%`,
              width: `${L.scale * 100}%`,
              transform: `translate(-50%, -50%) rotate(${L.rotation || 0}deg)${L.flipX ? ' scaleX(-1)' : ''}`,
              transformOrigin: 'center',
              zIndex: L.zIndex ?? 1,
              objectFit: 'contain',
              pointerEvents: 'none',
            }}
          />
        )
      })}

      {textOverlays.map((o) => {
        const L = { ...DEFAULT_TEXT_LAYOUT, ...(o.layout || {}) }
        const st = o.style || {}
        return (
          <div
            key={o.textOverlayId}
            style={{
              position: 'absolute',
              left: `${L.x * 100}%`,
              top: `${L.y * 100}%`,
              width: `${L.width * 100}%`,
              transform: `translate(-50%, -50%) rotate(${L.rotation || 0}deg)`,
              transformOrigin: 'center',
              zIndex: L.zIndex ?? 100,
              fontSize: h ? L.fontSize * h : `${L.fontSize * 100}cqh`,
              lineHeight: 1.3,
              textAlign: L.align || 'center',
              color: st.color || '#111111',
              background: st.backgroundColor || 'transparent', // 자막 배경 박스(none=투명, 렌더와 동일)
              borderRadius: h ? (st.borderRadius ?? 0.02) * h : `${(st.borderRadius ?? 0.02) * 100}cqh`,
              padding: h ? (st.padding ?? 0.02) * h : `${(st.padding ?? 0.02) * 100}cqh`,
              fontFamily: "'Hakgyoansim Dunggeunmiso', sans-serif", // 자막 전용 폰트(Regular)
              fontWeight: 400, // Regular 만 사용(굵게 X)
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              pointerEvents: 'none',
              boxSizing: 'border-box',
            }}
          >
            {o.text}
          </div>
        )
      })}
    </div>
  )
}

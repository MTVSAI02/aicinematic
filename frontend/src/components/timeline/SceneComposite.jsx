// 읽기전용 미니 합성: 배경 위에 캐릭터를 저장된 layout(정규화)대로 겹쳐 보여준다.
// %(정규화) 좌표를 그대로 써서 카드 썸네일/상세 등 어떤 크기에서도 동일 배치로 스케일된다.
// (scene-editor SceneStage의 편집 버전과 같은 배치를 읽기전용으로 재현)

const DEFAULT_LAYOUT = { x: 0.5, y: 0.55, scale: 0.28, rotation: 0, zIndex: 1, flipX: false }

export default function SceneComposite({ backgroundUrl, characters = [], className, emptyText = '배경 없음' }) {
  return (
    <div className={className} style={{ position: 'relative', overflow: 'hidden' }}>
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
              width: `${L.scale * 100}%`, // 컨테이너 너비 대비 비율 → 높이는 자동(비율 유지)
              transform: `translate(-50%, -50%) rotate(${L.rotation || 0}deg)${L.flipX ? ' scaleX(-1)' : ''}`,
              transformOrigin: 'center',
              zIndex: L.zIndex ?? 1,
              objectFit: 'contain',
              pointerEvents: 'none',
            }}
          />
        )
      })}
    </div>
  )
}

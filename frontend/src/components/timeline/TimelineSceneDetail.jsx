import { useEffect, useRef, useState } from 'react'
import styles from './Timeline.module.css'
import DurationControl from './DurationControl'
import SceneComposite from './SceneComposite'
import CueTimingEditor from './CueTimingEditor'

// 전체 미리보기 재생 큐: 씬 order 순 → cueOrder 순 → items(sourceItemIndex 순) → audioUrl 있는 것만.
// (전체 미리보기는 전 씬을 훑으므로 audio 도 전 씬을 순서대로 이어서 재생한다.)
function buildAudioQueue(scenes) {
  const list = [...(scenes ?? [])].sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
  const urls = []
  for (const s of list) {
    const cues = [...(s.cueTimings ?? [])].sort((a, b) => a.cueOrder - b.cueOrder)
    for (const c of cues) {
      for (const it of c.items ?? []) {
        if (it.audioUrl) urls.push(it.audioUrl)
      }
    }
  }
  return urls
}

// 선택한 씬 상세: 왼쪽 = 큰 미리보기(기존 UI 유지), 오른쪽 = 씬 정보 / 재생 길이 / 자막 타이밍.
// 미리보기 재생 시 기존 화면/자막 흐름은 그대로 두고, 선택 씬의 TTS audio 를 순서대로 함께 재생한다.
export default function TimelineSceneDetail({ scene, allScenes, saveStatus, playback, onDurationChange, onCueTimingChange, onAutoSplitCues, onFitToAudio }) {
  const [selectedCue, setSelectedCue] = useState(null)

  // ── 선택 씬 음성 순차 재생(기존 재생/정지에 얹음) ──
  const audioRef = useRef(null)
  const queueRef = useRef([])
  const idxRef = useRef(0)

  const playCurrent = () => {
    const q = queueRef.current
    if (idxRef.current >= q.length) return
    let a = audioRef.current
    if (!a) {
      a = new Audio()
      audioRef.current = a
    }
    a.src = q[idxRef.current]
    a.onended = () => {
      idxRef.current += 1
      playCurrent()
    }
    a.onerror = () => {
      idxRef.current += 1
      playCurrent()
    }
    a.play().catch(() => {
      idxRef.current += 1
      playCurrent()
    })
  }
  const startAudio = () => {
    queueRef.current = buildAudioQueue(allScenes && allScenes.length ? allScenes : [scene])
    idxRef.current = 0
    if (queueRef.current.length) playCurrent()
  }
  const resumeAudio = () => {
    const a = audioRef.current
    if (a && a.src) a.play().catch(() => {})
    else startAudio()
  }
  const pauseAudio = () => audioRef.current?.pause()
  const stopAudio = () => {
    const a = audioRef.current
    if (a) {
      a.pause()
      a.onended = null
      a.onerror = null
      a.src = ''
    }
    idxRef.current = 0
  }

  // 선택 씬이 바뀌면 cue 필터만 초기화(전체 미리보기 음성은 전 씬을 이어 재생하므로 중단하지 않음)
  useEffect(() => {
    setSelectedCue(null)
  }, [scene?.sceneId])
  // 언마운트 시 재생 중인 audio 정리
  useEffect(() => () => stopAudio(), [])

  if (!scene) {
    return <div className={styles.detail}><span className={styles.empty}>씬을 선택하세요.</span></div>
  }

  const pb = playback ?? {}
  const engaged = pb.engaged && pb.scene // 재생/일시정지 중이면 재생 씬을 보여줌
  const previewScene = engaged ? pb.scene : scene
  const previewChars = previewScene.characters ?? []
  const previewAllOverlays = previewScene.textOverlays ?? []
  // 미리보기 자막: 재생 중이면 현재 시간의 cue만, 아니면 수동 선택 cue(없으면 전체)
  const shownOverlays = engaged
    ? (pb.visibleCueOrders ? previewAllOverlays.filter((o) => pb.visibleCueOrders.has(o.cueOrder)) : [])
    : (selectedCue == null ? previewAllOverlays : previewAllOverlays.filter((o) => o.cueOrder === selectedCue))

  const allOverlays = scene.textOverlays ?? []
  const rs = scene.readyStatus ?? {}
  const statusLine = [
    ['배경', rs.hasBackground],
    ['캐릭터', rs.hasCharacters],
    ['텍스트', rs.hasText],
    ['음성', rs.audioStatus === 'ready'],
  ]
  const fmt = (v) => (v ?? 0).toFixed(1)
  const hasSceneAudio = buildAudioQueue(allScenes && allScenes.length ? allScenes : [scene]).length > 0

  // 기존 재생/정지 컨트롤에 audio 제어를 함께 건다.
  const handlePlay = () => {
    if (engaged) resumeAudio()
    else startAudio() // 처음 재생: 선택 씬 audio 큐 처음부터
    pb.onPlay?.()
  }
  const handlePause = () => {
    pauseAudio()
    pb.onPause?.()
  }
  const handleStop = () => {
    stopAudio()
    pb.onStop?.()
  }

  return (
    <div className={styles.detail}>
      {/* 왼쪽: 미리보기 + 전체 재생 컨트롤 (기존 UI 유지, 음성만 추가) */}
      <div className={styles.detailPreview}>
        <div className={styles.detailPreviewLabel}>
          {engaged
            ? <>재생 중 · 씬 {previewScene.order}</>
            : <>선택한 씬 미리보기{selectedCue != null && <span className={styles.cueShown}> · 씬 {scene.order}-{selectedCue} 자막만</span>}</>}
        </div>

        <SceneComposite
          className={styles.detailStage}
          backgroundUrl={previewScene.background?.imageUrl}
          characters={previewChars}
          textOverlays={shownOverlays}
        />

        {/* 재생 컨트롤 + 상태 */}
        <div className={styles.playBar}>
          {!engaged ? (
            <button type="button" className={styles.playMain} onClick={handlePlay} disabled={!pb.total}>
              ▶ 전체 미리보기
            </button>
          ) : (
            <>
              {pb.playing ? (
                <button type="button" className={styles.playBtn} onClick={handlePause}>⏸ 일시정지</button>
              ) : (
                <button type="button" className={styles.playBtn} onClick={handlePlay}>▶ 재생</button>
              )}
              <button type="button" className={styles.playBtn} onClick={handleStop}>■ 정지</button>
            </>
          )}
        </div>
        {!hasSceneAudio && (
          <span className={styles.playNote}>아직 생성된 음성이 없습니다. (보이스 페이지에서 목소리를 확정해주세요)</span>
        )}

        {engaged && (
          <div className={styles.playStatus}>
            <span>씬 {pb.sceneIndex + 1} / {pb.sceneCount}</span>
            <span>전체 {fmt(pb.globalTime)} / {fmt(pb.total)}초</span>
            <span>씬 {fmt(pb.localTime)} / {fmt(pb.sceneDuration)}초</span>
          </div>
        )}

        {previewChars.length > 0 && (
          <div className={styles.detailChars}>
            {previewChars.map((c) => (
              <span key={c.characterId} className={styles.chip}>
                {c.imageUrl && <img className={styles.chipAvatar} src={c.imageUrl} alt="" draggable={false} />}
                {c.name}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* 오른쪽: 씬 정보 + 재생 길이 + 자막 타이밍 (선택 씬 기준 — 재생과 무관하게 편집 가능) */}
      <div className={styles.detailPanel}>
        <div className={styles.detailHeadRow}>
          <div className={styles.detailTitle}>씬 {scene.order}</div>
          <div className={styles.badges}>
            {statusLine.map(([label, ok]) => (
              <span key={label} className={`${styles.badge}${ok ? '' : ` ${styles.badgeWarn}`}`}>
                {label} {ok ? '✅' : '⚠'}
              </span>
            ))}
          </div>
        </div>

        <p className={styles.detailText}>{scene.textPreview || '텍스트 없음'}</p>

        <div className={styles.detailSection}>
          <div className={styles.detailTitle}>재생 길이</div>
          <DurationControl duration={scene.duration} onChange={(d) => onDurationChange(scene.sceneId, d)} />
        </div>

        <CueTimingEditor
          sceneOrder={scene.order}
          duration={scene.duration ?? 3}
          cueTimings={scene.cueTimings ?? []}
          saveStatus={saveStatus}
          selectedCue={selectedCue}
          onSelectCue={setSelectedCue}
          onChange={(cueOrder, patch) => onCueTimingChange(scene.sceneId, cueOrder, patch)}
          onAutoSplit={() => onAutoSplitCues(scene.sceneId)}
          onFitToAudio={() => onFitToAudio(scene.sceneId)}
        />
      </div>
    </div>
  )
}

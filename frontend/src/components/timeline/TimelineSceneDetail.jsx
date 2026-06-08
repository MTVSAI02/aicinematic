import { useEffect, useRef, useState } from 'react'
import styles from './Timeline.module.css'
import DurationControl from './DurationControl'
import SceneComposite from './SceneComposite'
import CueTimingEditor from './CueTimingEditor'
import { mediaUrl } from '@/utils/mediaUrl'

// 전역 오디오 스케줄: 각 음성 item 을 자막 cue.startSec 와 "동일한 시간축"(절대 globalStartSec)에 배치한다.
// 자막은 마스터 시계(previewTime)로 표시되므로, 오디오도 같은 시계에 종속시켜야 누적 밀림이 없다.
// globalStart = (이전 씬 duration 합) + cue.startSec + (같은 cue 앞 item 들의 audioDurationSec 합).
// (렌더의 _collect_audio_inputs 와 동일한 배치 규칙 — 미리보기/렌더 타이밍 일치)
// 전체 미리보기 재생 큐: 씬 order 순 → cueOrder 순 → items(sourceItemIndex 순) → audioUrl 있는 것만.
// 각 음성에 "전체 타임라인 기준 시작 offset"(= 이전 씬 합 + cue.startSec + cue 내 앞 item 길이 합)을 함께 담는다.
// 이 offset + audio.currentTime 이 자막 시계(previewTime)가 되어, 자막이 재생 중 음성을 따라가게 한다(음성=master).
// (offset 은 cue.startSec 기반이라 audioDurationSec 가 없어도 단일 item cue 는 정확. 같은 cue 내 다중 item 만 길이 누적 사용)
function buildAudioQueue(scenes) {
  const list = [...(scenes ?? [])].sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
  const items = []
  let sceneStart = 0
  for (const s of list) {
    const cues = [...(s.cueTimings ?? [])].sort((a, b) => a.cueOrder - b.cueOrder)
    for (const c of cues) {
      const cueStart = sceneStart + (c.startSec ?? 0)
      let itemOff = 0
      const cueItems = [...(c.items ?? [])].sort((a, b) => (a.sourceItemIndex ?? 0) - (b.sourceItemIndex ?? 0))
      for (const it of cueItems) {
        if (it.audioUrl) items.push({ url: mediaUrl(it.audioUrl), offset: cueStart + itemOff })
        itemOff += it.audioDurationSec || 0
      }
    }
    sceneStart += s.duration ?? 0
  }
  return items
}

// 선택한 씬 상세: 왼쪽 = 큰 미리보기(기존 UI 유지), 오른쪽 = 씬 정보 / 재생 길이 / 자막 타이밍.
// 미리보기 재생 시 기존 화면/자막 흐름은 그대로 두고, 선택 씬의 TTS audio 를 순서대로 함께 재생한다.
export default function TimelineSceneDetail({ scene, allScenes, saveStatus, playback, onDurationChange, onCueTimingChange, onAutoSplitCues, onFitToAudio }) {
  const [selectedCue, setSelectedCue] = useState(null)

  // ── 선택 씬 음성 순차 재생 (음성=master, 자막 follower) ──
  // 미리보기 음성은 원격(mongsil)에서 받아오므로 트랙마다 즉석 로딩하면 전환 때 멈춤(갭)이 생긴다.
  // → 재생 시작 시 모든 음성을 blob 으로 통째 받아 메모리에서 재생(네트워크 의존 제거 = 갭 없음).
  //    단 첫 트랙은 autoplay 정책상 사용자 클릭(제스처) 안에서 즉시 재생해야 하므로 네트워크 src 로 먼저 튼다.
  const audioRef = useRef(null) // 현재 재생 중 element
  const audiosRef = useRef([]) // element 배열(each._offset = 전체 타임라인 시작 위치)
  const blobUrlsRef = useRef([]) // 생성한 objectURL (정리용)
  const idxRef = useRef(0)
  const wantIdxRef = useRef(-1) // blob 아직 안 와서 재생 대기 중인 index

  const setAudioClock = (v) => {
    const ref = playback?.audioClockRef
    if (ref) ref.current = v
  }
  const playIndex = (i) => {
    const list = audiosRef.current
    if (i >= list.length) {
      setAudioClock(null) // 끝 → 음성 master 해제(rAF 가 남은 길이 진행 후 정지)
      return
    }
    idxRef.current = i
    const a = list[i]
    audioRef.current = a
    a.ontimeupdate = () => setAudioClock(a._offset + a.currentTime)
    a.onended = () => playIndex(i + 1)
    a.onerror = () => playIndex(i + 1)
    if (!a.src) {
      wantIdxRef.current = i // blob 아직 → 준비되면 재생(아래 fetch 핸들러가 호출)
      return
    }
    wantIdxRef.current = -1
    try {
      a.currentTime = 0
    } catch {
      /* 메타데이터 로딩 전이면 무시 */
    }
    a.play().catch(() => playIndex(i + 1))
  }
  const startAudio = () => {
    stopAudio()
    const q = buildAudioQueue(allScenes && allScenes.length ? allScenes : [scene])
    const els = q.map((it) => {
      const a = new Audio()
      a.preload = 'auto'
      a._offset = it.offset
      return a
    })
    audiosRef.current = els
    if (els.length) {
      els[0].src = q[0].url // 0번은 네트워크 src 로 즉시 재생(제스처 → autoplay OK)
      playIndex(0)
    }
    // 전부 blob 으로 받아 element src 교체 → 이후 트랙은 메모리에서 재생(갭 없음)
    q.forEach((it, i) => {
      fetch(it.url)
        .then((r) => (r.ok ? r.blob() : null))
        .then((b) => {
          if (!b) return
          const a = audiosRef.current[i]
          if (!a) return // 이미 stop
          if (idxRef.current === i && !a.paused) return // 재생 중인 트랙은 안 건드림
          const obj = URL.createObjectURL(b)
          blobUrlsRef.current.push(obj)
          a.src = obj
          if (wantIdxRef.current === i) playIndex(i) // 그 트랙 차례인데 기다리고 있었으면 재생
        })
        .catch(() => {})
    })
  }
  const resumeAudio = () => {
    const a = audioRef.current
    if (a && a.src) a.play().catch(() => {})
    else startAudio()
  }
  const pauseAudio = () => audioRef.current?.pause()
  const stopAudio = () => {
    audiosRef.current.forEach((a) => {
      a.pause()
      a.onended = null
      a.onerror = null
      a.ontimeupdate = null
      a.src = ''
    })
    blobUrlsRef.current.forEach((u) => URL.revokeObjectURL(u))
    blobUrlsRef.current = []
    audiosRef.current = []
    audioRef.current = null
    idxRef.current = 0
    wantIdxRef.current = -1
    setAudioClock(null)
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
                {c.imageUrl && <img className={styles.chipAvatar} src={mediaUrl(c.imageUrl)} alt="" draggable={false} />}
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

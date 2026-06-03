import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useStoryStore from '@/store/useStoryStore'
import { getTimeline, updateTimeline } from '@/api/timeline'
import { getVoiceLocks } from '@/api/stories'
import { getApiErrorMessage } from '@/utils/apiError'
import TimelineSceneCard from '@/components/timeline/TimelineSceneCard'
import TimelineSceneDetail from '@/components/timeline/TimelineSceneDetail'
import { clampDuration } from '@/components/timeline/DurationControl'
import { sceneOffsets, resolvePlayback } from '@/components/timeline/previewPlayback'
import styles from '@/components/timeline/Timeline.module.css'

// /timeline — 스토리보드 기반 타임라인. 순서는 스토리 원본 고정(재배치 없음).
// 역할: 씬 재생 길이(duration) + 자막 cue 그룹 타이밍(startSec/durationSec) 조절. 변경 시 자동 저장.
// (자막 텍스트/위치/cueOrder는 scene-editor 소유 — 여기선 "시간"만. 멀티트랙/오디오/렌더 없음)
const round3 = (v) => Math.round(v * 1000) / 1000
const clampNum = (v, lo, hi) => Math.min(hi, Math.max(lo, v))

export default function TimelinePage() {
  const navigate = useNavigate()
  const storyId = useStoryStore((s) => s.storyId)

  const [scenes, setScenes] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [saveStatus, setSaveStatus] = useState('idle') // idle | saving | saved | failed
  const [voiceReady, setVoiceReady] = useState(true) // 모든 필수 대상 locked(=nextStepEnabled) 인지

  // ── 브라우저 미리보기 재생(렌더링 아님): React state + requestAnimationFrame ──
  const [playing, setPlaying] = useState(false)
  const [previewTime, setPreviewTime] = useState(0) // 전체 타임라인 기준 현재 시간(초)
  const timeRef = useRef(0) // rAF 루프의 실제 시간 소스(state는 렌더용)

  const latestScenes = useRef([]) // debounce 시점의 최신 scenes 참조
  const lastSaved = useRef([]) // 마지막으로 서버에 반영된 값(실패 시 rollback 기준)
  const saveTimer = useRef(null) // duration 연타 합치는 debounce 타이머
  const saveSeq = useRef(0) // 최신 요청만 반영(늦게 온 stale 응답 무시)
  useEffect(() => {
    latestScenes.current = scenes
  }, [scenes])

  // 진입/스토리 변경 시 타임라인 조회. 스토리가 바뀌면 선택 씬도 첫 씬으로 리셋한다.
  useEffect(() => {
    if (!storyId) return
    if (saveTimer.current) clearTimeout(saveTimer.current) // 이전 스토리의 보류 저장 취소
    setLoading(true)
    setError('')
    setSaveStatus('idle')
    setPlaying(false) // 스토리 바뀌면 재생 중지 + 처음으로
    timeRef.current = 0
    setPreviewTime(0)
    getTimeline(storyId)
      .then((res) => {
        const list = res.scenes ?? []
        setScenes(list)
        lastSaved.current = list
        setSelectedId(list[0]?.sceneId ?? null)
      })
      .catch((e) => setError(getApiErrorMessage(e)))
      .finally(() => setLoading(false))
    // 보이스 잠금 완료 여부(미완료면 상단 안내) — 실패는 무시(타임라인 자체는 보여줌)
    getVoiceLocks(storyId)
      .then((d) => setVoiceReady(Boolean(d?.allLocked)))
      .catch(() => setVoiceReady(true))
  }, [storyId])

  // 언마운트 시 보류 중인 저장 타이머 정리
  useEffect(() => () => saveTimer.current && clearTimeout(saveTimer.current), [])

  const { starts, total: totalDuration } = useMemo(() => sceneOffsets(scenes), [scenes])
  const selectedScene = scenes.find((s) => s.sceneId === selectedId) || null

  // 재생/일시정지 시 previewTime>0 → "재생 흐름 보기" 모드(미리보기가 재생 씬을 따라감)
  const engaged = playing || previewTime > 0
  const pb = engaged ? resolvePlayback(scenes, starts, totalDuration, previewTime) : null

  // rAF 루프: dt 만큼 시간 누적, 끝에 도달하면 정지. timeRef 가 시간의 source of truth.
  useEffect(() => {
    if (!playing) return
    let raf = 0
    let last = 0
    const tick = (ts) => {
      if (!last) last = ts
      const dt = (ts - last) / 1000
      last = ts
      const nt = timeRef.current + dt
      if (nt >= totalDuration) {
        timeRef.current = totalDuration
        setPreviewTime(totalDuration)
        setPlaying(false)
        return
      }
      timeRef.current = nt
      setPreviewTime(nt)
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [playing, totalDuration])

  function handlePreviewPlay() {
    if (totalDuration <= 0) return
    if (timeRef.current >= totalDuration) {
      timeRef.current = 0 // 끝에서 다시 누르면 처음부터
      setPreviewTime(0)
    }
    setPlaying(true)
  }
  function handlePreviewPause() {
    setPlaying(false)
  }
  function handlePreviewStop() {
    setPlaying(false)
    timeRef.current = 0
    setPreviewTime(0)
  }

  const playback = {
    engaged,
    playing,
    globalTime: previewTime,
    total: totalDuration,
    sceneCount: scenes.length,
    scene: pb?.scene ?? null,
    sceneIndex: pb?.index ?? -1,
    localTime: pb?.localTime ?? 0,
    sceneDuration: pb?.duration ?? 0,
    visibleCueOrders: pb?.visibleCueOrders ?? null,
    onPlay: handlePreviewPlay,
    onPause: handlePreviewPause,
    onStop: handlePreviewStop,
  }

  // 저장(debounce): 모든 씬의 duration + cueTimings 전송. cueTimings 은 씬 duration 안으로 클램프(서버 422 방지).
  // 늦게 도착한 이전 응답이 최신 값을 덮지 않도록 saveSeq 가드, 실패 시 lastSaved 로 rollback.
  function persist() {
    setSaveStatus('saving')
    setError('')
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      const seq = ++saveSeq.current
      const payload = latestScenes.current.map((s) => ({
        sceneId: s.sceneId,
        duration: s.duration,
        cueTimings: (s.cueTimings ?? [])
          .map((t) => {
            const start = clampNum(t.startSec, 0, s.duration)
            const dur = round3(Math.min(t.durationSec, s.duration - start))
            return dur > 0 ? { cueOrder: t.cueOrder, startSec: round3(start), durationSec: dur } : null
          })
          .filter(Boolean),
      }))
      updateTimeline(storyId, payload)
        .then((res) => {
          if (seq !== saveSeq.current) return // 더 최신 요청 진행 중 → 버림
          const saved = res.scenes ?? latestScenes.current
          setScenes(saved)
          lastSaved.current = saved
          setSaveStatus('saved')
        })
        .catch((e) => {
          if (seq !== saveSeq.current) return
          setScenes(lastSaved.current) // 마지막 저장 성공 값으로 rollback
          setSaveStatus('failed')
          setError(getApiErrorMessage(e))
        })
    }, 350)
  }

  function handleDurationChange(sceneId, dur) {
    const d = clampDuration(dur)
    setScenes((cur) => cur.map((s) => (s.sceneId === sceneId ? { ...s, duration: d } : s)))
    persist()
  }

  // cue 타이밍 한 항목 변경(startSec/durationSec). 텍스트/위치/cueOrder는 안 건드림.
  function handleCueTimingChange(sceneId, cueOrder, patch) {
    setScenes((cur) =>
      cur.map((s) =>
        s.sceneId !== sceneId
          ? s
          : { ...s, cueTimings: (s.cueTimings ?? []).map((t) => (t.cueOrder === cueOrder ? { ...t, ...patch } : t)) },
      ),
    )
    persist()
  }

  // 씬 duration 을 cue 개수만큼 균등 분할
  function handleAutoSplitCues(sceneId) {
    setScenes((cur) =>
      cur.map((s) => {
        if (s.sceneId !== sceneId) return s
        const cues = [...(s.cueTimings ?? [])].sort((a, b) => a.cueOrder - b.cueOrder)
        if (cues.length === 0) return s
        const each = s.duration / cues.length
        return {
          ...s,
          cueTimings: cues.map((t, i) => ({ ...t, startSec: round3(i * each), durationSec: round3(each) })),
        }
      }),
    )
    persist()
  }

  // 음성 길이에 맞추기: 각 cue durationSec = audioDurationSec(없으면 기존 유지), startSec 누적, 씬 duration = 합계.
  // 합계가 30초(씬 최대)를 넘으면 적용/저장하지 않고 안내만(무리한 축소 방지).
  function handleFitToAudio(sceneId) {
    setError('')
    const scene = latestScenes.current.find((s) => s.sceneId === sceneId)
    const cues = [...(scene?.cueTimings ?? [])].sort((a, b) => a.cueOrder - b.cueOrder)
    if (cues.length === 0) return
    // cue 길이 = 그 cue items 음성 합계(없으면 기존 자막 길이 유지)
    const lengths = cues.map((c) => {
      const sum = (c.items ?? []).reduce((a, it) => a + (it.audioDurationSec || 0), 0)
      return sum > 0 ? round3(sum) : c.durationSec
    })
    const total = round3(lengths.reduce((a, b) => a + b, 0))
    if (total > 30) {
      setError('음성 길이 합계가 씬 최대 길이 30초를 초과합니다. 자막을 줄이거나 씬을 나눠주세요.')
      return
    }
    let acc = 0
    const newCues = cues.map((t, i) => {
      const startSec = round3(acc)
      acc += lengths[i]
      return { ...t, startSec, durationSec: round3(lengths[i]) }
    })
    const newDuration = clampDuration(total)
    setScenes((cur) => cur.map((s) => (s.sceneId === sceneId ? { ...s, duration: newDuration, cueTimings: newCues } : s)))
    persist()
  }

  if (!storyId) {
    return (
      <div className={styles.page}>
        <h1 className={styles.title}>타임라인</h1>
        <p className={styles.empty}>스토리를 먼저 입력해 주세요.</p>
        <button className={styles.btn} onClick={() => navigate('/story-input')}>스토리 입력하러 가기</button>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>타임라인</h1>
        <span className={styles.summary}>
          총 <b>{scenes.length}</b>개 씬 · 총 <b>{totalDuration.toFixed(1)}</b>초
          {' · '}
          <span
            className={`${styles.saveStatus} ${
              saveStatus === 'saving'
                ? styles.saveSaving
                : saveStatus === 'failed'
                  ? styles.saveFailed
                  : styles.saveSaved
            }`}
          >
            {saveStatus === 'saving' && '저장 중…'}
            {saveStatus === 'saved' && '저장 완료'}
            {saveStatus === 'failed' && '저장 실패'}
            {saveStatus === 'idle' && '자동 저장'}
          </span>
        </span>
      </div>
      <p className={styles.guide}>
        씬 순서는 스토리 원본 그대로입니다. 카드를 <b>클릭</b>해 아래에서 <b>재생 길이</b>와 <b>자막 타이밍</b>을 조절하세요. (변경 시 자동 저장)
      </p>

      {!voiceReady && (
        <div className={styles.voiceGuard}>
          <span>
            보이스 설정이 완료되지 않았습니다. 보이스 페이지에서 나레이션과 모든 캐릭터의 목소리를 확정해주세요.
          </span>
          <button className={styles.btnSecondary} onClick={() => navigate('/voice')}>
            보이스 페이지로 이동
          </button>
        </div>
      )}

      {loading && scenes.length === 0 ? (
        <p className={styles.empty}>불러오는 중…</p>
      ) : scenes.length === 0 ? (
        <p className={styles.empty}>씬이 없습니다. 스토리를 먼저 입력해 주세요.</p>
      ) : (
        <>
          <div className={styles.track}>
            {scenes.map((scene) => (
              <TimelineSceneCard
                key={scene.sceneId}
                scene={scene}
                selected={scene.sceneId === selectedId}
                playing={playback.scene?.sceneId === scene.sceneId}
                onSelect={setSelectedId}
              />
            ))}
          </div>

          <TimelineSceneDetail
            scene={selectedScene}
            allScenes={scenes}
            saveStatus={saveStatus}
            playback={playback}
            onDurationChange={handleDurationChange}
            onCueTimingChange={handleCueTimingChange}
            onAutoSplitCues={handleAutoSplitCues}
            onFitToAudio={handleFitToAudio}
          />
        </>
      )}

      {error && <p className={styles.error}>{error} (다시 시도해 주세요)</p>}

      <div className={styles.actions}>
        <button className={styles.btnSecondary} onClick={() => navigate('/scene-editor')}>← 씬 편집</button>
        <button className={styles.btn} onClick={() => navigate('/render')}>영상 생성 →</button>
      </div>
    </div>
  )
}

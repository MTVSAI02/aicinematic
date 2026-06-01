import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useStoryStore from '@/store/useStoryStore'
import { getTimeline, updateTimeline } from '@/api/timeline'
import { getApiErrorMessage } from '@/utils/apiError'
import TimelineSceneCard from '@/components/timeline/TimelineSceneCard'
import TimelineSceneDetail from '@/components/timeline/TimelineSceneDetail'
import { clampDuration } from '@/components/timeline/DurationControl'
import styles from '@/components/timeline/Timeline.module.css'

// /timeline — 스토리보드 기반 타임라인. 순서는 스토리 원본 고정(재배치 없음).
// 역할: 각 씬의 재생 길이(duration) 조절 + 준비 상태(배경/캐릭터/텍스트) 확인. 변경 시 자동 저장.
// (순서 재배치/멀티트랙/자유배치/오디오 파형/렌더링 없음 — 스펙 범위)
export default function TimelinePage() {
  const navigate = useNavigate()
  const storyId = useStoryStore((s) => s.storyId)

  const [scenes, setScenes] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [saveStatus, setSaveStatus] = useState('idle') // idle | saving | saved | failed

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
    getTimeline(storyId)
      .then((res) => {
        const list = res.scenes ?? []
        setScenes(list)
        lastSaved.current = list
        setSelectedId(list[0]?.sceneId ?? null)
      })
      .catch((e) => setError(getApiErrorMessage(e)))
      .finally(() => setLoading(false))
  }, [storyId])

  // 언마운트 시 보류 중인 저장 타이머 정리
  useEffect(() => () => saveTimer.current && clearTimeout(saveTimer.current), [])

  const totalDuration = scenes.reduce((sum, s) => sum + (s.duration ?? 3), 0)
  const selectedScene = scenes.find((s) => s.sceneId === selectedId) || null

  // duration 변경: optimistic 반영 즉시, 서버 저장은 debounce(연타 합산).
  // 늦게 도착한 이전 응답이 최신 값을 덮지 않도록 saveSeq 가드, 실패 시 lastSaved 로 rollback.
  function handleDurationChange(sceneId, dur) {
    const d = clampDuration(dur)
    setScenes((cur) => cur.map((s) => (s.sceneId === sceneId ? { ...s, duration: d } : s)))
    setSaveStatus('saving')
    setError('')
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      const seq = ++saveSeq.current
      const payload = latestScenes.current.map((s) => ({ sceneId: s.sceneId, duration: s.duration }))
      updateTimeline(storyId, payload)
        .then((res) => {
          if (seq !== saveSeq.current) return // 더 최신 요청이 진행 중 → 이 응답은 버림
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
        씬 순서는 스토리 원본 그대로입니다. 카드를 <b>클릭</b>해 아래에서 <b>재생 길이</b>를 조절하세요. (변경 시 자동 저장)
      </p>

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
                onSelect={setSelectedId}
              />
            ))}
          </div>

          <TimelineSceneDetail scene={selectedScene} onDurationChange={handleDurationChange} />
        </>
      )}

      {error && <p className={styles.error}>{error} (다시 시도해 주세요)</p>}

      <div className={styles.actions}>
        <button className={styles.btnSecondary} onClick={() => navigate('/scene-editor')}>← 씬 편집</button>
        <button className={styles.btn} onClick={() => navigate('/export')}>출력 준비 →</button>
      </div>
    </div>
  )
}

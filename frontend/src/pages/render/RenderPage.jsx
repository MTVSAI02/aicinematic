import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useStoryStore from '@/store/useStoryStore'
import { getRenderStatus, startRender } from '@/api/render'
import { getTimeline } from '@/api/timeline'
import { pollJob } from '@/utils/pollJob'
import { getApiErrorMessage } from '@/utils/apiError'
import styles from './RenderPage.module.css'

// /render — 최종 영상 생성·확인 페이지. (타임라인 자막 + 잠근 보이스 TTS 음성을 합성한 mp4)
// 상태: loading | idle(생성 전) | rendering(생성 중) | done(완료) | error(실패).
// 기능 로직(POST/GET render, polling, lastRender 복원, 다운로드)은 그대로. UI 구성만 정리.
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''
const RENDER_STEPS = ['렌더링 작업 요청 중', '프레임 합성 중', 'MP4 인코딩 중', '결과 영상 준비 중']

// 다운로드 파일명용 안전 변환: 금지 문자 제거 → 공백 정리 → 길이 제한 → 비면 storyId → 'mongle-video'.
function safeFileName(title, storyId) {
  let name = (title ?? '')
    .toString()
    .replace(/[/\\:*?"<>|]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
  if (name.length > 80) name = name.slice(0, 80).trim()
  return name || storyId || 'mongle-video'
}

function fmtDate(iso) {
  return iso ? String(iso).slice(0, 10) : '' // YYYY-MM-DD
}

export default function RenderPage() {
  const navigate = useNavigate()
  const storyId = useStoryStore((s) => s.storyId)
  const storyTitle = useStoryStore((s) => s.storyTitle)

  const [status, setStatus] = useState('loading') // loading | idle | rendering | done | error
  const [jobStatus, setJobStatus] = useState('')
  const [video, setVideo] = useState(null) // { renderId, videoUrl, duration, createdAt? }
  const [error, setError] = useState('')
  const [summary, setSummary] = useState(null) // { sceneCount, totalDuration }
  const [renderStep, setRenderStep] = useState(0)
  const abortRef = useRef(null)

  useEffect(() => () => abortRef.current?.abort(), [])

  // 진입: 기존 렌더(lastRender) 복원 + 헤더 요약(씬 개수/총 길이) 조회
  useEffect(() => {
    if (!storyId) return
    let alive = true
    setStatus('loading')
    getRenderStatus(storyId)
      .then((res) => {
        if (!alive) return
        if (res?.lastRender) {
          setVideo(res.lastRender)
          setStatus('done')
        } else {
          setStatus('idle')
        }
      })
      .catch(() => alive && setStatus('idle'))
    getTimeline(storyId)
      .then((tl) => alive && setSummary({ sceneCount: (tl.scenes ?? []).length, totalDuration: tl.totalDuration ?? 0 }))
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [storyId])

  // 렌더링 중 단계 문구(코스메틱 — 실제 진행률은 없음, 안내용)
  useEffect(() => {
    if (status !== 'rendering') return
    setRenderStep(0)
    const id = setInterval(() => setRenderStep((s) => Math.min(s + 1, RENDER_STEPS.length - 1)), 2200)
    return () => clearInterval(id)
  }, [status])

  async function handleRender() {
    if (!storyId) return
    setStatus('rendering')
    setError('')
    setJobStatus('pending')
    const controller = new AbortController()
    abortRef.current = controller
    try {
      const { jobId } = await startRender(storyId)
      const job = await pollJob(jobId, { signal: controller.signal, onStatus: (j) => setJobStatus(j.status) })
      // 완료 후 createdAt 포함된 canonical lastRender 로 갱신(실패 시 job.result 로 폴백)
      let result = null
      try {
        result = (await getRenderStatus(storyId))?.lastRender
      } catch {
        /* getRenderStatus 실패 시 job.result 사용 */
      }
      setVideo(result ?? job.result)
      setStatus('done')
    } catch (e) {
      if (e?.aborted) return
      setError(
        e?.timedOut
          ? '렌더링이 오래 걸리고 있습니다. 잠시 후 다시 시도해 주세요.'
          : e?.detail || getApiErrorMessage(e),
      )
      setStatus('error')
    }
  }

  // 다운로드: cross-origin 에서 <a download> 가 무시되므로 blob 으로 받아 저장(파일명=스토리 제목).
  async function handleDownload() {
    if (!video?.videoUrl) return
    const url = `${BASE_URL}${video.videoUrl}`
    try {
      const res = await fetch(url)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const blob = await res.blob()
      const objectUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = objectUrl
      a.download = `${safeFileName(storyTitle, storyId)}.mp4`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(objectUrl)
    } catch {
      window.open(url, '_blank')
    }
  }

  if (!storyId) {
    return (
      <div className={styles.page}>
        <header className={styles.header}>
          <h1 className={styles.title}>영상 생성</h1>
        </header>
        <div className={styles.card}>
          <div className={styles.emptyIcon}>🎬</div>
          <h2 className={styles.cardTitle}>스토리를 먼저 입력해 주세요</h2>
          <p className={styles.cardDesc}>영상을 생성하려면 먼저 스토리가 필요합니다.</p>
          <button className={styles.btnPrimary} onClick={() => navigate('/story-input')}>스토리 입력하러 가기</button>
        </div>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      {/* 헤더 카드: 제목 + 스토리 + 설명 + 요약 배지 */}
      <header className={styles.header}>
        <div className={styles.headTop}>
          <h1 className={styles.title}>영상 생성</h1>
          {storyTitle && <span className={styles.storyTitle}>{storyTitle}</span>}
        </div>
        <p className={styles.lead}>
          타임라인에서 설정한 씬 순서, 배경, 캐릭터, 자막 타이밍에 잠근 보이스의 TTS 음성까지 합성해 MP4 영상을 생성합니다.
        </p>
        <div className={styles.badges}>
          {summary && <span className={styles.badge}>총 {summary.sceneCount}개 씬</span>}
          {summary && <span className={styles.badge}>총 {summary.totalDuration.toFixed(1)}초</span>}
          <span className={styles.badge}>음성 포함</span>
          <span className={styles.badge}>MP4</span>
        </div>
      </header>

      {/* 상태별 본문 카드 */}
      {status === 'loading' && (
        <div className={styles.card}>
          <p className={styles.muted}>불러오는 중…</p>
        </div>
      )}

      {status === 'idle' && (
        <div className={styles.card}>
          <div className={styles.emptyIcon}>🎬</div>
          <h2 className={styles.cardTitle}>아직 생성된 영상이 없습니다</h2>
          <p className={styles.cardDesc}>
            현재 타임라인 설정과 잠근 보이스의 TTS 음성을 합성해 영상을 생성합니다.
          </p>
          <button className={styles.btnPrimary} onClick={handleRender}>▶ 음성 포함 영상 생성</button>
        </div>
      )}

      {status === 'rendering' && (
        <div className={styles.card}>
          <div className={styles.spinner} aria-hidden="true" />
          <h2 className={styles.cardTitle}>영상 생성 중</h2>
          <p className={styles.cardDesc}>
            현재 타임라인을 영상으로 합성하고 있습니다. 배경·캐릭터·자막·음성을 MP4로 변환 중입니다.
          </p>
          <ul className={styles.steps}>
            {RENDER_STEPS.map((s, i) => (
              <li key={s} className={`${styles.step} ${i <= renderStep ? styles.stepActive : ''}`}>
                {i < renderStep ? '✓ ' : i === renderStep ? '· ' : ''}{s}
              </li>
            ))}
          </ul>
          <p className={styles.muted}>
            {jobStatus === 'pending' ? '대기열에서 작업을 준비하고 있습니다…' : '렌더링 중입니다…'}
          </p>
        </div>
      )}

      {status === 'done' && video && (
        <div className={styles.card}>
          <div className={styles.resultHead}>
            <h2 className={styles.cardTitle}>최종 영상 미리보기</h2>
            {storyTitle && <span className={styles.muted}>{storyTitle}</span>}
          </div>
          <div className={styles.videoWrap}>
            {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
            <video className={styles.video} controls src={`${BASE_URL}${video.videoUrl}`} />
          </div>
          <div className={styles.metaRow}>
            <span className={styles.badge}>음성 포함</span>
            <span className={styles.meta}>길이 {Number(video.duration).toFixed(1)}초</span>
            {video.createdAt && <span className={styles.meta}>생성일 {fmtDate(video.createdAt)}</span>}
          </div>
          <p className={styles.note}>타임라인에 잠근 보이스의 TTS 음성이 합성된 MP4입니다.</p>
          <div className={styles.actions}>
            <button className={styles.btnPrimary} onClick={handleDownload}>다운로드</button>
            <button className={styles.btnOutline} onClick={handleRender}>다시 생성</button>
          </div>
        </div>
      )}

      {status === 'error' && (
        <div className={`${styles.card} ${styles.errorCard}`}>
          <div className={styles.emptyIcon}>⚠️</div>
          <h2 className={styles.cardTitle}>영상 생성에 실패했습니다</h2>
          <p className={styles.cardDesc}>{error}</p>
          <button className={styles.btnPrimary} onClick={handleRender}>다시 시도</button>
        </div>
      )}

      {/* 하단: 타임라인으로 */}
      <div className={styles.footer}>
        <button className={styles.btnSecondary} onClick={() => navigate('/timeline')}>← 타임라인</button>
      </div>
    </div>
  )
}

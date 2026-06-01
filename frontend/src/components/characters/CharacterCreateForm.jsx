import { useEffect, useRef, useState } from 'react'
import useCharacterStore from '@/store/useCharacterStore'
import * as characterApi from '@/api/characters'
import { pollJob } from '@/utils/pollJob'
import { getApiErrorMessage } from '@/utils/apiError'
// 캐릭터 페이지 공용 스타일 모듈 공유 (기존 디자인 톤 유지)
import styles from '@/pages/character/CharacterPage.module.css'

// Job 상태별 안내 문구. (비동기 Job: pending→running→completed/failed)
const JOB_STATUS_TEXT = {
  pending: '생성 대기 중입니다.',
  running: '캐릭터를 생성 중입니다.',
  completed: '캐릭터 생성이 완료되었습니다.',
  failed: '캐릭터 생성에 실패했습니다.',
}

export default function CharacterCreateForm() {
  const setCharacters = useCharacterStore((s) => s.setCharacters)

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [appearancePrompt, setAppearancePrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [jobStatus, setJobStatus] = useState(null)
  const [error, setError] = useState('')

  // 언마운트 시 진행 중 폴링 취소 (setState-on-unmounted 방지)
  const abortRef = useRef(null)
  useEffect(() => () => abortRef.current?.abort(), [])

  const trimmedName = name.trim()
  const trimmedPrompt = appearancePrompt.trim()
  const canSubmit = !!trimmedName && !!trimmedPrompt && !loading

  // 사용자에게 비활성화 이유를 알려주는 visible validation 메시지
  const validationMessage = loading
    ? ''
    : !trimmedName
      ? '캐릭터 이름을 입력해주세요.'
      : !trimmedPrompt
        ? '외형 프롬프트를 입력해주세요.'
        : ''

  async function handleCreate() {
    if (!canSubmit) return
    setLoading(true)
    setError('')
    setJobStatus(null)
    try {
      // 1. 생성 Job 요청 → jobId 수신 (비동기: 즉시 pending 반환)
      const job = await characterApi.generateCharacter({
        name: trimmedName,
        description: description.trim(),
        appearancePrompt: trimmedPrompt,
      })
      setJobStatus(job.status)

      // 2. completed/failed 까지 폴링 (pending/running 동안 상태 갱신)
      abortRef.current = new AbortController()
      await pollJob(job.jobId, {
        onStatus: (j) => setJobStatus(j.status),
        signal: abortRef.current.signal,
      })

      // 3. 완료 → 캐릭터 목록 다시 동기화 + 폼 초기화
      const list = await characterApi.getCharacters()
      setCharacters(list)
      setName('')
      setDescription('')
      setAppearancePrompt('')
    } catch (e) {
      if (e.aborted) return // 언마운트 취소 → 무시
      if (e.timedOut) {
        // 실패가 아니라 "아직 생성 중" — 백엔드 Job은 계속 진행 중일 수 있음
        setError('생성이 오래 걸리고 있어요. 잠시 후 캐릭터 라이브러리를 새로고침해 확인하세요.')
        return
      }
      // pollJob 실패 시 e.detail = 백엔드 실제 실패 원인(job.error)
      setJobStatus('failed')
      setError(getApiErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.form}>
      <label className={styles.label}>
        이름
        <input
          className={styles.input}
          placeholder="어린왕자"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <label className={styles.label}>
        외형 설명
        <input
          className={styles.input}
          placeholder="예: 금발 단발의 작은 소년, 초록 외투"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </label>
      <label className={styles.label}>
        외형 프롬프트
        <textarea
          className={styles.textarea}
          placeholder={"blonde short hair, small boy, green coat, full body, white background\n자세할수록 더 정확하게 생성됩니다."}
          value={appearancePrompt}
          onChange={(e) => setAppearancePrompt(e.target.value)}
        />
      </label>
      <button className={styles.btn} onClick={handleCreate} disabled={!canSubmit}>
        {loading ? '생성 중...' : '캐릭터 생성'}
      </button>

      {validationMessage && <p className={styles.validation}>{validationMessage}</p>}
      {jobStatus && (
        <p className={styles.status}>
          {JOB_STATUS_TEXT[jobStatus] ?? `상태: ${jobStatus}`}
        </p>
      )}
      {error && <p className={styles.error}>{error}</p>}
    </div>
  )
}

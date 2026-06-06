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
      {/* 1. 캐릭터의 이름을 입력해주세요 */}
      <div className={styles.section}>
        <h2 className={styles.stepTitle}>
          <span className={styles.stepBadge}>1</span>캐릭터의 이름을 입력해주세요
        </h2>
        <div className={styles.nameInputRow}>
          <select className={styles.roleSelect}>
            <option value="">역할</option>
            <option value="protagonist">주인공</option>
            <option value="supporting">조연</option>
            <option value="extra">엑스트라</option>
          </select>
          <input
            className={styles.input}
            placeholder="어린왕자"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
      </div>

      {/* 2. 캐릭터가 어떻게 생겼나요? */}
      <div className={styles.section}>
        <h2 className={styles.stepTitle}>
          <span className={styles.stepBadge}>2</span>캐릭터가 어떻게 생겼나요?
        </h2>
        <div className={styles.textareaWrapper}>
          <textarea
            className={styles.textarea}
            placeholder="노란색의 짧고 곱슬거리는 머리카락, 맑고 순수한 얼굴, 초록색 코트(소매와 장식 부분에 붉은색 포인트), 검은 장화, 긴 노란색 머플러, 흰색 점프수트를 입은 소년 "
            value={appearancePrompt}
            onChange={(e) => setAppearancePrompt(e.target.value)}
          />
        </div>
        <div className={styles.formFooterRow}>
          <span className={styles.formFooterHint}>캐릭터의 머리, 눈색, 입은 옷, 장신구등을 지정해서 써 줄 수록 비슷한 캐릭터가 완성이 됩니다</span>
          
          <button className={styles.generateBtn} onClick={handleCreate} disabled={!canSubmit || loading}>
            {loading ? (
              <>
                <span className={styles.spinner} /> 생성 중...
              </>
            ) : (
              '목소리 만들기 →'
            )}
          </button>
        </div>
      </div>

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

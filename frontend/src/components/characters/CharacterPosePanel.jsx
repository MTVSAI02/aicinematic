import { useEffect, useRef, useState } from 'react'
import useCharacterStore from '@/store/useCharacterStore'
import * as characterApi from '@/api/characters'
import { pollJob } from '@/utils/pollJob'
import { getApiErrorMessage } from '@/utils/apiError'
import { mediaUrl } from '@/utils/mediaUrl'
import styles from './CharacterPosePanel.module.css'

const JOB_STATUS_TEXT = {
  pending: '포즈 생성 대기 중입니다.',
  running: '포즈를 생성 중입니다.',
  completed: '포즈 생성이 완료되었습니다.',
  failed: '포즈 생성에 실패했습니다.',
}

// 지정한 캐릭터(characterId)의 포즈를 생성/조회/적용한다. (드롭다운 없이 외부에서 캐릭터를 정해줌)
// 프론트는 characterId + posePrompt 만 보낸다(image_path 는 다루지 않음). 원본 캐릭터 이미지는 그대로 유지.
// onApplyPose(poseId|null): 이 씬 캐릭터에 포즈 적용/해제(null=기본). currentPoseId: 현재 적용된 포즈.
export default function CharacterPosePanel({ characterId, currentPoseId = null, onApplyPose }) {
  const characters = useCharacterStore((s) => s.characters)
  const character = characters.find((c) => c.characterId === characterId)

  const [posePrompt, setPosePrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [jobStatus, setJobStatus] = useState(null)
  const [error, setError] = useState('')
  const [poses, setPoses] = useState([])

  const abortRef = useRef(null)
  useEffect(() => () => abortRef.current?.abort(), [])

  // 캐릭터가 바뀌면 상태 초기화 + 포즈 목록 로드
  useEffect(() => {
    setPosePrompt('')
    setJobStatus(null)
    setError('')
    if (!characterId) {
      setPoses([])
      return
    }
    let alive = true
    characterApi
      .getCharacterPoses(characterId)
      .then((list) => alive && setPoses(list))
      .catch(() => alive && setPoses([]))
    return () => {
      alive = false
    }
  }, [characterId])

  const canSubmit = !!characterId && !!posePrompt.trim() && !loading

  async function handleGenerate() {
    if (!canSubmit) return
    setLoading(true)
    setError('')
    setJobStatus(null)
    try {
      const job = await characterApi.generateCharacterPose(characterId, {
        posePrompt: posePrompt.trim(),
      })
      setJobStatus(job.status)
      abortRef.current = new AbortController()
      await pollJob(job.jobId, {
        onStatus: (j) => setJobStatus(j.status),
        signal: abortRef.current.signal,
      })
      const list = await characterApi.getCharacterPoses(characterId)
      setPoses(list)
      setPosePrompt('')
    } catch (e) {
      if (e.aborted) return
      if (e.timedOut) {
        setError('생성이 오래 걸리고 있어요. 잠시 후 다시 확인하세요.')
        return
      }
      setJobStatus('failed')
      setError(getApiErrorMessage(e)) // 400(원본 경로 없음)/404/502 detail 그대로
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.posePanel}>
      {/* 1. 보유 중인 포즈 */}
      {onApplyPose && (
        <div className={styles.posesSection}>
          <span className={styles.sectionTitle}>보유 중인 포즈</span>
          <div className={styles.poseGrid}>
            <div
              className={`${styles.poseCard} ${!currentPoseId ? styles.poseCardActive : ''}`}
              onClick={() => onApplyPose(null)}
              role="button"
            >
              {character?.imageUrl && (
                <img className={styles.poseImg} src={mediaUrl(character.imageUrl)} alt="" draggable={false} />
              )}
              <span className={styles.posePrompt}>기본 포즈</span>
            </div>
            {poses.map((p) => (
              <div
                key={p.poseId}
                className={`${styles.poseCard} ${currentPoseId === p.poseId ? styles.poseCardActive : ''}`}
                onClick={() => onApplyPose(p.poseId)}
                role="button"
              >
                <img className={styles.poseImg} src={mediaUrl(p.imageUrl)} alt="" draggable={false} />
                <span className={styles.posePrompt} title={p.posePrompt}>
                  {p.posePrompt}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 구분선 */}
      <hr className={styles.divider} />

      {/* 2. 포즈 생성 폼 */}
      <div className={styles.generatorSection}>
        <span className={styles.sectionTitle}>새 포즈 생성</span>
        <textarea
          className={styles.textarea}
          placeholder={'이 캐릭터의 새 포즈 (예: running in the snow / sitting and smiling)'}
          value={posePrompt}
          onChange={(e) => setPosePrompt(e.target.value)}
          rows={2}
        />
        <button className={styles.btn} onClick={handleGenerate} disabled={!canSubmit}>
          {loading ? '생성 중...' : '포즈 생성'}
        </button>
        {jobStatus && <p className={styles.status}>{JOB_STATUS_TEXT[jobStatus] ?? `상태: ${jobStatus}`}</p>}
        {error && <p className={styles.error}>{error}</p>}
      </div>
    </div>
  )
}

import { useEffect, useRef, useState } from 'react'
import useCharacterStore from '@/store/useCharacterStore'
import * as characterApi from '@/api/characters'
import { pollJob } from '@/utils/pollJob'
import { getApiErrorMessage } from '@/utils/apiError'
import { mediaUrl } from '@/utils/mediaUrl'
import styles from '@/pages/character/CharacterPage.module.css'

const JOB_STATUS_TEXT = {
  pending: '포즈 생성 대기 중입니다.',
  running: '포즈를 생성 중입니다.',
  completed: '포즈 생성이 완료되었습니다.',
  failed: '포즈 생성에 실패했습니다.',
}

export default function CharacterPoseSection() {
  const selectedCharacterId = useCharacterStore((s) => s.selectedCharacterId)
  const characters = useCharacterStore((s) => s.characters)
  const selectCharacter = useCharacterStore((s) => s.selectCharacter)
  const setLightboxPose = useCharacterStore((s) => s.setLightboxPose)

  const [poses, setPoses] = useState([])
  const [posePrompt, setPosePrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [jobStatus, setJobStatus] = useState(null)
  const [error, setError] = useState('')
  const [deletingId, setDeletingId] = useState(null)

  const abortRef = useRef(null)

  // 컴포넌트 언마운트 시 폴링 취소
  useEffect(() => {
    return () => {
      abortRef.current?.abort()
    }
  }, [])

  // 캐릭터 선택 변경 시 포즈 목록 조회 및 초기화
  useEffect(() => {
    if (!selectedCharacterId) {
      setPoses([])
      return
    }

    setLoading(false)
    setError('')
    setJobStatus(null)
    setPosePrompt('')

    characterApi
      .getCharacterPoses(selectedCharacterId)
      .then((list) => {
        setPoses(list)
      })
      .catch((err) => {
        setError(`포즈 목록을 불러오지 못했습니다. ${getApiErrorMessage(err)}`)
      })
  }, [selectedCharacterId])

  // 포즈 삭제: 씬에서 사용 중이면 백엔드가 409 로 막는다(메시지 표시). 안 쓰는 포즈만 삭제됨.
  const handleDeletePose = async (pose) => {
    if (!window.confirm('이 포즈를 삭제할까요?')) return
    setError('')
    setDeletingId(pose.poseId)
    try {
      await characterApi.deleteCharacterPose(selectedCharacterId, pose.poseId)
      setPoses((prev) => prev.filter((p) => p.poseId !== pose.poseId))
    } catch (err) {
      setError(getApiErrorMessage(err)) // 씬에서 사용 중(409) 등
    } finally {
      setDeletingId(null)
    }
  }

  const selectedCharacter = characters.find(
    (c) => c.characterId === selectedCharacterId
  )

  const trimmedPrompt = posePrompt.trim()
  const validationMessage =
    !loading && !trimmedPrompt && selectedCharacterId
      ? '포즈 설명을 입력해주세요.'
      : ''

  async function handleCreatePose() {
    if (!trimmedPrompt || !selectedCharacterId || loading) return
    setLoading(true)
    setError('')
    setJobStatus(null)

    try {
      // 1. 포즈 생성 Job 요청
      const job = await characterApi.generateCharacterPose(selectedCharacterId, {
        posePrompt: trimmedPrompt,
      })
      setJobStatus(job.status)

      // 2. Job 완료까지 폴링
      abortRef.current = new AbortController()
      await pollJob(job.jobId, {
        onStatus: (j) => setJobStatus(j.status),
        signal: abortRef.current.signal,
      })

      // 3. 포즈 목록 새로고침
      const list = await characterApi.getCharacterPoses(selectedCharacterId)
      setPoses(list)
      setPosePrompt('')
    } catch (e) {
      if (e.aborted) return
      if (e.timedOut) {
        setError(
          '포즈 생성이 오래 걸리고 있어요. 잠시 후 포즈 목록을 확인해 보세요.'
        )
        return
      }
      setJobStatus('failed')
      setError(getApiErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className={styles.poseSection}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <h2 className={styles.poseTitle} style={{ margin: 0 }}>
          캐릭터 포즈 만들기
        </h2>
        {characters.length > 0 && (
          <select
            className={styles.roleSelect}
            style={{ width: '180px' }}
            value={selectedCharacterId || ''}
            onChange={(e) => selectCharacter(e.target.value || null)}
          >
            <option value="">캐릭터 선택</option>
            {characters.map((c) => (
              <option key={c.characterId} value={c.characterId}>
                {c.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {!selectedCharacter ? (
        <div className={styles.poseSelectGuide}>
          캐릭터 라이브러리에서 캐릭터를 선택하면 다양한 포즈를 생성할 수 있어요.
        </div>
      ) : (
        <div className={styles.poseContent}>
          <div className={styles.poseFormRow}>
            <input
              type="text"
              className={styles.input}
              placeholder="예: 눈밭을 신나게 뛰어노는 모습, 손을 흔들며 환하게 웃는 모습"
              value={posePrompt}
              onChange={(e) => setPosePrompt(e.target.value)}
              disabled={loading}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleCreatePose()
                }
              }}
            />
            <button
              className={styles.generateBtn}
              onClick={handleCreatePose}
              disabled={!trimmedPrompt || loading}
            >
              {loading ? (
                <>
                  <span className={styles.spinner} /> 생성 중...
                </>
              ) : (
                '포즈 만들기 →'
              )}
            </button>
          </div>

          {validationMessage && (
            <p className={styles.poseValidation}>{validationMessage}</p>
          )}
          {jobStatus && (
            <p className={styles.poseStatus}>
              {JOB_STATUS_TEXT[jobStatus] ?? `상태: ${jobStatus}`}
            </p>
          )}
          {error && <p className={styles.poseError}>{error}</p>}

          <div className={styles.poseListSection}>
            <h3 className={styles.poseListHeader}>생성된 포즈 목록</h3>
            {poses.length === 0 ? (
              <p className={styles.emptyPoses}>
                아직 생성된 포즈가 없어요. 첫 번째 포즈를 만들어 보세요!
              </p>
            ) : (
              <ul className={styles.poseGrid}>
                {poses.map((pose) => (
                  <li
                    key={pose.poseId}
                    className={styles.poseCard}
                    onClick={() => setLightboxPose(pose)}
                  >
                    <div className={styles.poseThumb}>
                      {pose.imageUrl ? (
                        <img
                          src={mediaUrl(pose.imageUrl)}
                          alt={pose.posePrompt}
                          className={styles.poseThumbImg}
                        />
                      ) : (
                        <span className={styles.thumbEmpty}>이미지 준비 중</span>
                      )}
                    </div>
                    <p className={styles.posePrompt} title={pose.posePrompt}>
                      {pose.posePrompt}
                    </p>
                    {/* 캐릭터 카드와 동일한 수정/삭제 버튼 행 (수정은 추후 기능 — 현재 비활성) */}
                    <div className={styles.cardActions} onClick={(e) => e.stopPropagation()}>
                      <button className={styles.cardBtn} disabled title="준비 중">
                        수정
                      </button>
                      <button
                        className={styles.cardBtn}
                        onClick={() => handleDeletePose(pose)}
                        disabled={deletingId === pose.poseId}
                      >
                        {deletingId === pose.poseId ? '삭제 중…' : '삭제'}
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </section>
  )
}

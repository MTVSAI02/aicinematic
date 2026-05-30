import { useState } from 'react'
import useBackgroundStore from '@/store/useBackgroundStore'
import * as backgroundApi from '@/api/backgrounds'
import { getApiErrorMessage } from '@/utils/apiError'
import styles from '@/pages/background/BackgroundPage.module.css'

// 후보가 선택되면 이름을 입력해 라이브러리에 저장한다.
export default function BackgroundSaveForm() {
  const {
    selectedCandidateId, loading,
    setBackgrounds, setSelectedCandidateId, setLoading, setError,
  } = useBackgroundStore()

  const [name, setName] = useState('')
  const [savedMessage, setSavedMessage] = useState('')
  const [localError, setLocalError] = useState('')

  const canSave = !!selectedCandidateId && !!name.trim() && !loading

  async function handleSave() {
    if (!canSave) return
    setLocalError('')
    setSavedMessage('')
    setError(null)
    setLoading(true)
    try {
      await backgroundApi.saveBackground({
        candidateId: selectedCandidateId,
        name: name.trim(),
      })
      // 저장 후 라이브러리 갱신
      const list = await backgroundApi.getBackgrounds()
      setBackgrounds(list)
      setSelectedCandidateId(null)
      setName('')
      setSavedMessage('배경이 라이브러리에 저장되었습니다.')
    } catch (e) {
      setLocalError(getApiErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.form}>
      <label className={styles.label}>
        배경 이름
        <input
          className={styles.input}
          placeholder="별빛 사막 배경"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <button className={styles.btn} onClick={handleSave} disabled={!canSave}>
        선택한 배경 저장
      </button>

      {!selectedCandidateId && (
        <p className={styles.validation}>먼저 후보를 선택해주세요.</p>
      )}
      {selectedCandidateId && !name.trim() && (
        <p className={styles.validation}>배경 이름을 입력해주세요.</p>
      )}
      {savedMessage && <p className={styles.status}>{savedMessage}</p>}
      {localError && <p className={styles.error}>{localError}</p>}
    </div>
  )
}

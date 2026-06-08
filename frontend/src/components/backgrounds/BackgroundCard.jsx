import { useState } from 'react'
import useBackgroundStore from '@/store/useBackgroundStore'
import * as backgroundApi from '@/api/backgrounds'
import { getApiErrorMessage } from '@/utils/apiError'
import styles from '@/pages/background/BackgroundPage.module.css'

export default function BackgroundCard({ background }) {
  const selectedBackgroundId = useBackgroundStore((s) => s.selectedBackgroundId)
  const setSelectedBackgroundId = useBackgroundStore((s) => s.setSelectedBackgroundId)
  const updateBackgroundInStore = useBackgroundStore((s) => s.updateBackground)
  const removeBackground = useBackgroundStore((s) => s.removeBackground)

  const [editing, setEditing] = useState(false)
  const [editName, setEditName] = useState(background.name)
  const [error, setError] = useState('')

  const isSelected = background.backgroundId === selectedBackgroundId

  async function handleSaveEdit() {
    if (!editName.trim()) return
    setError('')
    try {
      const updated = await backgroundApi.updateBackground(background.backgroundId, {
        name: editName.trim(),
      })
      updateBackgroundInStore(background.backgroundId, updated)
      setEditing(false)
    } catch (e) {
      setError(getApiErrorMessage(e))
    }
  }

  async function handleDelete() {
    if (!window.confirm('이 배경을 삭제할까요?')) return
    setError('')
    try {
      await backgroundApi.deleteBackground(background.backgroundId)
      removeBackground(background.backgroundId)
    } catch (e) {
      setError(getApiErrorMessage(e))
    }
  }

  return (
    <li
      className={`${styles.card} ${isSelected ? styles.cardSelected : ''}`}
      onClick={() => setSelectedBackgroundId(background.backgroundId)}
    >
      <div className={styles.thumb}>
        {background.imageUrl ? (
          <img src={background.imageUrl} alt={background.name} className={styles.thumbImg} />
        ) : (
          <span className={styles.thumbEmpty}>이미지 준비 중</span>
        )}
      </div>

      {editing ? (
        <div className={styles.editForm} onClick={(e) => e.stopPropagation()}>
          <input
            className={styles.input}
            value={editName}
            placeholder="배경 이름"
            onChange={(e) => setEditName(e.target.value)}
          />
          <div className={styles.cardActions}>
            <button className={styles.cardBtn} onClick={handleSaveEdit} disabled={!editName.trim()}>
              저장
            </button>
            <button className={styles.cardBtn} onClick={() => setEditing(false)}>
              취소
            </button>
          </div>
        </div>
      ) : (
        <>
          <span className={styles.cardName}>{background.name}</span>
          <span className={styles.cardDesc}>{background.prompt}</span>
          {isSelected && <span className={styles.selectedBadge}>선택됨</span>}
          <div className={styles.cardActions} onClick={(e) => e.stopPropagation()}>
            <button className={styles.cardBtn} onClick={() => setEditing(true)}>수정</button>
            <button className={styles.cardBtn} onClick={handleDelete}>삭제</button>
          </div>
          {error && <span className={styles.error}>{error}</span>}
        </>
      )}
    </li>
  )
}

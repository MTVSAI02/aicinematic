import { useState } from 'react'
import useCharacterStore from '@/store/useCharacterStore'
import * as characterApi from '@/api/characters'
import { getApiErrorMessage } from '@/utils/apiError'
import styles from '@/pages/character/CharacterPage.module.css'

// 카드 안 인라인 수정 폼. name / appearancePrompt / description 을 수정한다.
// (imageUrl 은 AI 연동 결과용이라 일반 입력으로 노출하지 않는다)
export default function CharacterEditForm({ character, onDone }) {
  const updateCharacterInStore = useCharacterStore((s) => s.updateCharacter)

  const [editName, setEditName] = useState(character.name)
  const [editPrompt, setEditPrompt] = useState(character.appearancePrompt)
  const [editDescription, setEditDescription] = useState(character.description ?? '')
  const [error, setError] = useState('')

  const canSave = !!editName.trim() && !!editPrompt.trim()

  async function handleSave() {
    if (!canSave) return
    setError('')
    try {
      const updated = await characterApi.updateCharacter(character.characterId, {
        name: editName.trim(),
        appearancePrompt: editPrompt.trim(),
        description: editDescription.trim() || null, // 표시용 메타(비우면 해제)
      })
      updateCharacterInStore(character.characterId, updated)
      onDone()
    } catch (e) {
      setError(getApiErrorMessage(e))
    }
  }

  return (
    <div className={styles.editForm} onClick={(e) => e.stopPropagation()}>
      <input
        className={styles.input}
        value={editName}
        placeholder="이름"
        onChange={(e) => setEditName(e.target.value)}
      />
      <input
        className={styles.input}
        value={editPrompt}
        placeholder="외형 프롬프트 (ComfyUI 생성용)"
        onChange={(e) => setEditPrompt(e.target.value)}
      />
      <input
        className={styles.input}
        value={editDescription}
        placeholder="설명 (표시용, 선택)"
        onChange={(e) => setEditDescription(e.target.value)}
      />
      <div className={styles.cardActions}>
        <button className={styles.cardBtn} onClick={handleSave} disabled={!canSave}>
          저장
        </button>
        <button className={styles.cardBtn} onClick={onDone}>
          취소
        </button>
      </div>
      {error && <span className={styles.error}>{error}</span>}
    </div>
  )
}

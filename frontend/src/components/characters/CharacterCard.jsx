import { useState } from 'react'
import useCharacterStore from '@/store/useCharacterStore'
import * as characterApi from '@/api/characters'
import { getApiErrorMessage } from '@/utils/apiError'
import { mediaUrl } from '@/utils/mediaUrl'
import ConfirmModal from '@/components/common/ConfirmModal'
import CharacterEditForm from './CharacterEditForm'
import styles from '@/pages/character/CharacterPage.module.css'

export default function CharacterCard({ character }) {
  const selectedCharacterId = useCharacterStore((s) => s.selectedCharacterId)
  const selectCharacter = useCharacterStore((s) => s.selectCharacter)
  const removeCharacter = useCharacterStore((s) => s.removeCharacter)
  const setDetailModalCharacter = useCharacterStore((s) => s.setDetailModalCharacter)

  const [editing, setEditing] = useState(false)
  const [error, setError] = useState('')
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const isSelected = character.characterId === selectedCharacterId

  async function handleDelete() {
    setError('')
    setDeleting(true)
    try {
      await characterApi.deleteCharacter(character.characterId)
      removeCharacter(character.characterId) // 성공 시 목록에서 제거 → 이 카드 언마운트
    } catch (e) {
      setError(getApiErrorMessage(e))
      setDeleting(false)
      setConfirmOpen(false)
    }
  }

  return (
    <li
      className={`${styles.card} ${isSelected ? styles.cardSelected : ''}`}
      onClick={() => selectCharacter(character.characterId)}
    >
      <div 
        className={styles.thumb} 
        onClick={(e) => {
          e.stopPropagation()
          setDetailModalCharacter(character)
        }}
        title="클릭하여 크게 보기"
      >
        {character.imageUrl ? (
          <img src={mediaUrl(character.imageUrl)} alt={character.name} className={styles.thumbImg} />
        ) : (
          <span className={styles.thumbEmpty}>이미지 준비 중</span>
        )}
      </div>

      {editing ? (
        <CharacterEditForm character={character} onDone={() => setEditing(false)} />
      ) : (
        <>
          <span className={styles.cardName}>{character.name}</span>
          <span className={styles.cardDesc}>{character.appearancePrompt}</span>
          <span 
            className={styles.moreLink}
            onClick={(e) => {
              e.stopPropagation()
              setDetailModalCharacter(character)
            }}
          >
            더보기
          </span>
          {isSelected && <span className={styles.selectedBadge}>선택됨</span>}
          {/* 임시 수정/삭제 버튼 (디자인 확정 전) */}
          <div className={styles.cardActions} onClick={(e) => e.stopPropagation()}>
            <button className={styles.cardBtn} onClick={() => setEditing(true)}>
              수정
            </button>
            <button className={styles.cardBtn} onClick={() => setConfirmOpen(true)}>
              삭제
            </button>
          </div>
          {error && <span className={styles.error}>{error}</span>}
        </>
      )}

      {/* 공용 삭제 확인 모달 (카드 onClick 버블 방지 래퍼) */}
      <span onClick={(e) => e.stopPropagation()}>
        <ConfirmModal
          open={confirmOpen}
          title="이 캐릭터를 삭제할까요?"
          message={`'${character.name}' 캐릭터가 삭제됩니다.`}
          confirmText={deleting ? '삭제 중…' : '삭제하기'}
          variant="danger"
          busy={deleting}
          onConfirm={handleDelete}
          onCancel={() => {
            if (!deleting) setConfirmOpen(false)
          }}
        />
      </span>
    </li>
  )
}

import { useState } from 'react'
import useVoiceStore from '@/store/useVoiceStore'
import { assignNarratorVoiceToStory } from '@/api/stories'
import { assignVoiceToCharacter } from '@/api/characters'
import { updateVoice as apiUpdateVoice, deleteVoice as apiDeleteVoice } from '@/api/voices'
import { getApiErrorMessage } from '@/utils/apiError'
import styles from '@/pages/voice/VoicePage.module.css'

// 보이스 한 개 카드: 미리듣기 / 연결 / (preset 아니면) 수정·삭제.
// 연결 버튼은 선택된 대상의 accept 와 voiceType 이 일치할 때만 활성화된다.
export default function VoiceCard({ voice }) {
  const story = useVoiceStore((s) => s.story)
  const characters = useVoiceStore((s) => s.characters)
  const selectedTarget = useVoiceStore((s) => s.selectedTarget)
  const setNarratorVoiceId = useVoiceStore((s) => s.setNarratorVoiceId)
  const setCharacterVoiceId = useVoiceStore((s) => s.setCharacterVoiceId)
  const updateVoiceInStore = useVoiceStore((s) => s.updateVoice)
  const removeVoice = useVoiceStore((s) => s.removeVoice)
  const detachDeletedVoice = useVoiceStore((s) => s.detachDeletedVoice)
  const setMessage = useVoiceStore((s) => s.setMessage)
  const setError = useVoiceStore((s) => s.setError)

  const [editing, setEditing] = useState(false)
  const [editName, setEditName] = useState(voice.name)

  // 대상이 선택돼 있고, 대상이 받는 타입(accept)과 보이스 타입이 일치해야 연결 가능
  const canConnect =
    selectedTarget &&
    selectedTarget.accept === voice.voiceType &&
    (selectedTarget.type === 'narrator' || Boolean(selectedTarget.characterId))

  // 이 보이스가 현재 선택 대상에 이미 연결돼 있는지
  const connectedHere =
    selectedTarget &&
    (selectedTarget.type === 'narrator'
      ? story?.narratorVoiceId === voice.voiceId
      : characters.find((c) => c.characterId === selectedTarget.characterId)?.voiceId ===
        voice.voiceId)

  const hasSample = Boolean(voice.sampleAudioUrl)

  async function handleConnect() {
    setError(null)
    try {
      if (selectedTarget.type === 'narrator') {
        await assignNarratorVoiceToStory(story.storyId, { voiceId: voice.voiceId })
        setNarratorVoiceId(voice.voiceId)
        setMessage(`나레이션에 “${voice.name}”을(를) 연결했습니다.`)
      } else {
        await assignVoiceToCharacter(selectedTarget.characterId, { voiceId: voice.voiceId })
        setCharacterVoiceId(selectedTarget.characterId, voice.voiceId)
        setMessage(`${selectedTarget.name}에 “${voice.name}”을(를) 연결했습니다.`)
      }
    } catch (err) {
      setMessage(null)
      setError(getApiErrorMessage(err))
    }
  }

  async function handleSaveEdit() {
    if (!editName.trim()) return
    setError(null)
    try {
      const updated = await apiUpdateVoice(voice.voiceId, { name: editName.trim() })
      updateVoiceInStore(voice.voiceId, updated)
      setEditing(false)
    } catch (err) {
      setError(getApiErrorMessage(err))
    }
  }

  async function handleDelete() {
    if (!window.confirm('이 보이스를 삭제할까요?')) return
    setError(null)
    try {
      await apiDeleteVoice(voice.voiceId)
      removeVoice(voice.voiceId)
      // 백엔드 캐스케이드와 동일하게 로컬 참조도 정리 (stale voiceId 방지)
      detachDeletedVoice(voice.voiceId)
    } catch (err) {
      setError(getApiErrorMessage(err))
    }
  }

  return (
    <li className={`${styles.voiceCard} ${connectedHere ? styles.voiceCardConnected : ''}`}>
      <div className={styles.voiceHead}>
        <span className={styles.voiceName}>{voice.name}</span>
        {voice.isPreset && <span className={styles.badge}>기본</span>}
        <span className={styles.badgeType}>{voice.voiceType}</span>
      </div>

      {voice.description && <span className={styles.voiceDesc}>{voice.description}</span>}
      <span className={styles.voiceMeta}>상태: {voice.status}</span>

      {/* 미리듣기: sampleAudioUrl 있으면 재생, 없으면 "샘플 준비 중"(비활성) */}
      {hasSample ? (
        <audio className={styles.audio} controls src={voice.sampleAudioUrl} />
      ) : (
        <button className={styles.cardBtn} disabled>
          샘플 준비 중
        </button>
      )}

      {editing ? (
        <div className={styles.editForm}>
          <input
            className={styles.input}
            value={editName}
            placeholder="보이스 이름"
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
        <div className={styles.cardActions}>
          <button className={styles.cardBtn} onClick={handleConnect} disabled={!canConnect || connectedHere}>
            {connectedHere ? '연결됨' : '연결'}
          </button>
          {/* preset(isPreset=true)은 수정/삭제 불가 → 버튼 숨김 */}
          {!voice.isPreset && (
            <>
              <button className={styles.cardBtn} onClick={() => setEditing(true)}>
                수정
              </button>
              <button className={styles.cardBtn} onClick={handleDelete}>
                삭제
              </button>
            </>
          )}
        </div>
      )}
    </li>
  )
}

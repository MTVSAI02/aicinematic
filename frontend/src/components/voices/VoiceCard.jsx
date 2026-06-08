import { useState } from 'react'
import useVoiceStore from '@/store/useVoiceStore'
import { assignNarratorVoiceToStory } from '@/api/stories'
import { assignVoiceToCharacter } from '@/api/characters'
import { updateVoice as apiUpdateVoice, deleteVoice as apiDeleteVoice } from '@/api/voices'
import { getApiErrorMessage } from '@/utils/apiError'
import styles from '@/pages/voice/VoicePage.module.css'

// 미디어(/storage/...) 는 백엔드에서 서빙되므로 API 베이스 URL 을 붙여 절대경로로 만든다.
// (상대경로면 Vercel 도메인 기준으로 해석돼 배포 환경에서 재생이 안 된다 — RenderPage/VoiceInputPage 와 동일 처리)
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

// 보이스 한 개 카드: 미리듣기 / 연결 / (preset 아니면) 수정·삭제.
// 연결은 voiceType 과 무관하게 status==ready 면 가능(추천 태그일 뿐). 선택 대상이 locked 면 연결 비활성.
export default function VoiceCard({ voice }) {
  const story = useVoiceStore((s) => s.story)
  const characters = useVoiceStore((s) => s.characters)
  const selectedTarget = useVoiceStore((s) => s.selectedTarget)
  const voiceLocks = useVoiceStore((s) => s.voiceLocks)
  const refreshVoiceLocks = useVoiceStore((s) => s.refreshVoiceLocks)
  const setNarratorVoiceId = useVoiceStore((s) => s.setNarratorVoiceId)
  const setCharacterVoiceId = useVoiceStore((s) => s.setCharacterVoiceId)
  const updateVoiceInStore = useVoiceStore((s) => s.updateVoice)
  const removeVoice = useVoiceStore((s) => s.removeVoice)
  const detachDeletedVoice = useVoiceStore((s) => s.detachDeletedVoice)
  const setMessage = useVoiceStore((s) => s.setMessage)
  const setError = useVoiceStore((s) => s.setError)

  const [editing, setEditing] = useState(false)
  const [editName, setEditName] = useState(voice.name)

  // 연결 가능 조건은 voiceType 이 아니라 status 로 판단한다(추천 태그일 뿐).
  // 대상이 선택돼 있고 + 보이스가 ready 면 narrator/character 어디든 연결 가능.
  // 단 선택한 대상이 잠긴(locked) 상태면 연결을 바꿀 수 없다(잠금 해제 후 가능).
  const isReady = voice.status === 'ready'
  const selectedLock = voiceLocks.find((l) => l.targetId === selectedTarget?.targetId)
  const isLocked = selectedLock?.lockStatus === 'locked'
  const canConnect =
    selectedTarget &&
    isReady &&
    !isLocked &&
    (selectedTarget.type === 'narrator' || Boolean(selectedTarget.characterId))

  // 이 보이스가 현재 선택 대상에 이미 연결돼 있는지
  const connectedHere =
    selectedTarget &&
    (selectedTarget.type === 'narrator'
      ? story?.narratorVoiceId === voice.voiceId
      : characters.find((c) => c.characterId === selectedTarget.characterId)?.voiceId ===
        voice.voiceId)

  const hasSample = Boolean(voice.sampleAudioUrl)
  const isFailed = voice.status === 'failed'

  const recommendTag = voice.voiceType === 'narrator' ? '나레이션 추천' : '캐릭터 추천'
  const statusLabel = isReady ? 'ready (연결 가능)' : isFailed ? '생성 실패' : '생성 중'
  const targetName = selectedTarget?.type === 'narrator' ? '나레이션' : selectedTarget?.name
  const connectLabel = connectedHere
    ? '연결됨'
    : isLocked
      ? '잠금됨'
      : !isReady
        ? isFailed ? '연결 불가' : '생성 중'
        : selectedTarget
          ? `${targetName}에 연결`
          : '연결'

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
      // 대상 카드의 현재 목소리/상태 갱신
      await refreshVoiceLocks()
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
        <span className={styles.badgeType}>{recommendTag}</span>
      </div>

      {voice.description && <span className={styles.voiceDesc}>{voice.description}</span>}
      {voice.speakerLabel && <span className={styles.voiceMeta}>녹음: {voice.speakerLabel}</span>}
      <span className={styles.voiceMeta}>상태: {statusLabel}</span>

      {isFailed ? (
        /* 실패: 미리듣기/연결/수정 없음 — 안내 + 삭제만 */
        <>
          <p className={styles.failNote}>생성 실패 · AI 보이스 서버 연결 후 다시 생성해 주세요.</p>
          {!voice.isPreset && (
            <div className={styles.cardActions}>
              <button className={styles.cardBtn} onClick={handleDelete}>삭제</button>
            </div>
          )}
        </>
      ) : (
        <>
          {/* 미리듣기: sampleAudioUrl 있으면 재생, 없으면 "샘플 없음"(비활성).
              preset 샘플은 백엔드 storage/voices/{voiceId}/sample.wav 고정 파일, 클론은 AI 결과로 채워진다. */}
          {hasSample ? (
            // eslint-disable-next-line jsx-a11y/media-has-caption
            <audio className={styles.audio} controls src={`${BASE_URL}${voice.sampleAudioUrl}`} />
          ) : (
            <button className={styles.cardBtn} disabled>샘플 없음</button>
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
                <button className={styles.cardBtn} onClick={handleSaveEdit} disabled={!editName.trim()}>저장</button>
                <button className={styles.cardBtn} onClick={() => setEditing(false)}>취소</button>
              </div>
            </div>
          ) : (
            <div className={styles.cardActions}>
              <button className={styles.cardBtn} onClick={handleConnect} disabled={!canConnect || connectedHere}>
                {connectLabel}
              </button>
              {/* preset(isPreset=true)은 수정/삭제 불가 → 버튼 숨김 */}
              {!voice.isPreset && (
                <>
                  <button className={styles.cardBtn} onClick={() => setEditing(true)}>수정</button>
                  <button className={styles.cardBtn} onClick={handleDelete}>삭제</button>
                </>
              )}
            </div>
          )}
        </>
      )}
    </li>
  )
}

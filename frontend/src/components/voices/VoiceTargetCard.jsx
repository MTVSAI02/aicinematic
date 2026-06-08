import { useNavigate } from 'react-router-dom'
import useVoiceStore from '@/store/useVoiceStore'
import { assignNarratorVoiceToStory } from '@/api/stories'
import { assignVoiceToCharacter } from '@/api/characters'
import { lockVoiceTarget, unlockVoiceTarget } from '@/api/stories'
import { getApiErrorMessage } from '@/utils/apiError'
import { mediaUrl } from '@/utils/mediaUrl'
import styles from '@/pages/voice/VoicePage.module.css'

// lockStatus/ttsStatus → 카드 상태 문구
function statusLabel(lock) {
  if (lock.lockStatus === 'locked') {
    return (
      {
        generating: '음성 생성 중',
        ready: '음성 준비 완료',
        failed: '음성 생성 실패',
        stale: '수정됨 · 다시 잠가주세요',
      }[lock.ttsStatus] ?? '잠김'
    )
  }
  return lock.voiceId ? '연결됨' : '목소리 미설정'
}

// 보이스를 붙일 대상(나레이션/캐릭터) 카드. 대상별로 연결·잠금·해제를 처리한다.
export default function VoiceTargetCard({ lock }) {
  const navigate = useNavigate()
  const story = useVoiceStore((s) => s.story)
  const selectedTarget = useVoiceStore((s) => s.selectedTarget)
  const setSelectedTarget = useVoiceStore((s) => s.setSelectedTarget)
  const setNarratorVoiceId = useVoiceStore((s) => s.setNarratorVoiceId)
  const setCharacterVoiceId = useVoiceStore((s) => s.setCharacterVoiceId)
  const refreshVoiceLocks = useVoiceStore((s) => s.refreshVoiceLocks)
  const setMessage = useVoiceStore((s) => s.setMessage)
  const setError = useVoiceStore((s) => s.setError)

  const isNarration = lock.targetType === 'narration'
  const isLocked = lock.lockStatus === 'locked'
  const selectable = lock.matched && !isLocked
  const isSelected = selectedTarget?.targetId === lock.targetId

  function handleSelect() {
    if (!selectable) return
    setSelectedTarget({
      type: isNarration ? 'narrator' : 'character',
      name: lock.displayName,
      characterId: isNarration ? null : lock.targetId,
      targetType: lock.targetType,
      targetId: lock.targetId,
    })
  }

  async function run(action, okMessage) {
    setError(null)
    try {
      await action()
      await refreshVoiceLocks()
      if (okMessage) setMessage(okMessage)
    } catch (err) {
      setMessage(null)
      setError(getApiErrorMessage(err))
    }
  }

  function handleUnassign(e) {
    e.stopPropagation()
    run(async () => {
      if (isNarration) {
        await assignNarratorVoiceToStory(story.storyId, { voiceId: null })
        setNarratorVoiceId(null)
      } else {
        await assignVoiceToCharacter(lock.targetId, { voiceId: null })
        setCharacterVoiceId(lock.targetId, null)
      }
    }, `${lock.displayName} 보이스 연결을 해제했습니다.`)
  }

  function handleLock(e) {
    e.stopPropagation()
    run(
      () => lockVoiceTarget(story.storyId, lock.targetType, lock.targetId),
      `${lock.displayName} 목소리를 잠그고 음성을 준비합니다.`,
    )
  }

  function handleUnlock(e) {
    e.stopPropagation()
    run(
      () => unlockVoiceTarget(story.storyId, lock.targetType, lock.targetId),
      `${lock.displayName} 잠금을 해제했습니다.`,
    )
  }

  return (
    <div
      className={`${styles.targetCard} ${isSelected ? styles.targetCardSelected : ''} ${
        selectable ? '' : styles.targetCardDisabled
      }`}
      onClick={handleSelect}
    >
      <div className={styles.targetHead}>
        {isNarration ? (
          <span className={styles.targetIcon}>📖</span>
        ) : lock.imageUrl ? (
          <img className={styles.targetThumb} src={mediaUrl(lock.imageUrl)} alt={lock.displayName} />
        ) : (
          <span className={styles.targetIcon}>🎭</span>
        )}
        <span className={styles.targetName}>{lock.displayName}</span>
        <span className={styles.badge}>{isNarration ? '나레이션' : '캐릭터'}</span>
      </div>

      {/* 매칭 캐릭터 없음 → 캐릭터 먼저 생성 */}
      {!lock.matched ? (
        <>
          <span className={styles.failNote}>캐릭터가 아직 생성되지 않았습니다.</span>
          <div className={styles.cardActions} onClick={(e) => e.stopPropagation()}>
            <button className={styles.cardBtn} onClick={() => navigate('/character')}>
              캐릭터 페이지로 이동
            </button>
          </div>
        </>
      ) : (
        <>
          <span className={styles.currentVoice}>
            현재 목소리: {lock.voiceName ?? (lock.voiceId ? lock.voiceId : '목소리 미설정')}
          </span>
          <span
            className={
              lock.ttsStatus === 'failed'
                ? styles.failNote
                : isLocked
                  ? styles.message
                  : styles.voiceMeta
            }
          >
            상태: {statusLabel(lock)}
          </span>

          <div className={styles.cardActions} onClick={(e) => e.stopPropagation()}>
            {isLocked ? (
              <>
                <button className={styles.cardBtn} onClick={handleUnlock}>
                  잠금 해제
                </button>
                {lock.ttsStatus === 'failed' && (
                  <button className={styles.cardBtn} onClick={handleLock}>
                    다시 시도
                  </button>
                )}
              </>
            ) : (
              <>
                {lock.voiceId && (
                  <button className={styles.cardBtn} onClick={handleUnassign}>
                    연결 해제
                  </button>
                )}
                <button
                  className={styles.cardBtn}
                  onClick={handleLock}
                  disabled={!lock.voiceId}
                >
                  이 목소리로 잠금
                </button>
              </>
            )}
          </div>

          {!isLocked && !lock.voiceId && (
            <span className={styles.validation}>먼저 오른쪽에서 목소리를 선택해 연결해주세요.</span>
          )}
          {isLocked && (
            <span className={styles.validation}>잠긴 대상입니다. 변경하려면 잠금을 해제하세요.</span>
          )}
        </>
      )}

      {isSelected && (
        <span className={styles.selectedBadge}>선택됨 · 오른쪽에서 보이스를 고르세요</span>
      )}
    </div>
  )
}

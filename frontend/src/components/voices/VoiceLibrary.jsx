import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useVoiceStore from '@/store/useVoiceStore'
import VoiceCard from './VoiceCard'
import styles from '@/pages/voice/VoicePage.module.css'

// 연결할 목소리 선택 패널: 기본 제공 / 내가 만든 으로 구분(추천 태그는 카드에 작게, 연결 제한 아님).
// 연결 가능은 status==='ready' 로만 판단. 새 목소리는 /voice-input(음성 입력)에서 만든다.
export default function VoiceLibrary() {
  const navigate = useNavigate()
  const voices = useVoiceStore((s) => s.voices)
  const selectedTarget = useVoiceStore((s) => s.selectedTarget)
  const [showFailed, setShowFailed] = useState(false)

  const presets = voices.filter((v) => v.isPreset)
  const mine = voices.filter((v) => !v.isPreset)
  const mineActive = mine.filter((v) => v.status !== 'failed')
  const mineFailed = mine.filter((v) => v.status === 'failed')

  const targetLabel = selectedTarget
    ? selectedTarget.type === 'narrator' ? '나레이션' : selectedTarget.name
    : null

  return (
    <div>
      <button className={styles.btn} style={{ marginBottom: 6 }} onClick={() => navigate('/voice-input')}>
        + 새 목소리 만들기
      </button>
      <p className={styles.hint} style={{ marginBottom: 14 }}>
        새 목소리는 음성 입력 페이지에서 녹음 또는 업로드로 만들 수 있어요.
      </p>

      {/* 선택한 대상 안내 */}
      {targetLabel ? (
        <p className={styles.selectedBanner}>
          <b>{targetLabel}</b>에 연결할 목소리를 선택 중입니다.
        </p>
      ) : (
        <p className={styles.validation}>먼저 왼쪽에서 대상을 선택하세요. (ready 상태 목소리만 연결 가능)</p>
      )}

      {/* 기본 제공 보이스 */}
      <h3 className={styles.sectionTitle}>기본 제공 보이스</h3>
      <p className={styles.hint}>서비스에서 제공하는 기본 목소리예요. 추천 태그와 관계없이 원하는 대상에 연결할 수 있어요.</p>
      {presets.length === 0 ? (
        <p className={styles.empty}>기본 제공 보이스가 없습니다.</p>
      ) : (
        <ul className={styles.voiceList}>
          {presets.map((v) => <VoiceCard key={v.voiceId} voice={v} />)}
        </ul>
      )}

      {/* 내가 만든 보이스 */}
      <h3 className={styles.sectionTitle}>내가 만든 보이스</h3>
      <p className={styles.hint}>음성 입력 페이지에서 만든 목소리예요.</p>
      {mineActive.length === 0 && mineFailed.length === 0 ? (
        <div className={styles.emptyState}>
          <p className={styles.hint}>아직 만든 목소리가 없습니다. 음성 입력 페이지에서 목소리를 먼저 만들어보세요.</p>
          <button className={styles.cardBtn} onClick={() => navigate('/voice-input')}>새 목소리 만들기</button>
        </div>
      ) : (
        mineActive.length > 0 && (
          <ul className={styles.voiceList}>
            {mineActive.map((v) => <VoiceCard key={v.voiceId} voice={v} />)}
          </ul>
        )
      )}

      {/* 생성 실패 보이스 (접어두기) */}
      {mineFailed.length > 0 && (
        <div className={styles.failedSection}>
          <button className={styles.cardBtn} onClick={() => setShowFailed((s) => !s)}>
            생성 실패한 보이스 {mineFailed.length}개 {showFailed ? '접기 ▲' : '펼치기 ▼'}
          </button>
          {showFailed && (
            <ul className={styles.voiceList}>
              {mineFailed.map((v) => <VoiceCard key={v.voiceId} voice={v} />)}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}

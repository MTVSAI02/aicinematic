import { useEffect, useState } from 'react'
import { mediaUrl } from '@/utils/mediaUrl'
import styles from './Timeline.module.css'

// 선택한 씬의 cue 그룹별 타이밍 편집(1차: cue별 카드 = 자막 요약 + 숫자 입력 + 미니 타임바).
// 텍스트/위치/cueOrder는 건드리지 않음 — startSec/durationSec만. cue 클릭 시 미리보기 필터(onSelectCue).
const SAVE_LABEL = { saving: '저장 중…', saved: '자동 저장됨', failed: '저장 실패' }

// cue 의 TTS 상태(audio 없을 때) 안내
const TTS_NOTE = {
  generating: '음성 생성 중…',
  failed: '음성 생성 실패 · 보이스 페이지에서 다시 잠가주세요',
  stale: '보이스 설정이 변경됐어요 · 다시 잠가주세요',
  none: '아직 생성된 음성이 없습니다',
}

// 숫자 입력 1칸: 로컬 문자열 state 로 받아 입력 중 깨짐 방지.
// 유효 숫자일 때만 onCommit(부모 저장), 빈/비정상 값은 blur 시 원래 값으로 되돌림.
function CueField({ label, value, min, onCommit }) {
  const [text, setText] = useState(String(value))
  const [focused, setFocused] = useState(false)
  // 외부에서 값이 바뀌면(자동 균등 분할, 서버 반영) 동기화 — 단 입력 중에는 건드리지 않음
  useEffect(() => {
    if (!focused) setText(String(value))
  }, [value, focused])

  const handleChange = (e) => {
    const raw = e.target.value
    setText(raw)
    const n = Number(raw)
    if (raw.trim() !== '' && Number.isFinite(n)) onCommit(n) // 유효 숫자일 때만 반영(빈칸=0 방지)
  }
  const handleBlur = () => {
    setFocused(false)
    const n = Number(text)
    if (text.trim() === '' || !Number.isFinite(n)) setText(String(value)) // 비정상 입력 되돌림
  }

  return (
    <label className={styles.cueField} onClick={(e) => e.stopPropagation()}>
      {label}
      <input
        type="number"
        min={min}
        step="0.1"
        className={styles.cueInput}
        value={text}
        onFocus={() => setFocused(true)}
        onChange={handleChange}
        onBlur={handleBlur}
      />
      초
    </label>
  )
}

export default function CueTimingEditor({
  sceneOrder,
  duration,
  cueTimings,
  saveStatus = 'idle',
  selectedCue,
  onSelectCue,
  onChange, // (cueOrder, { startSec?|durationSec? })
  onAutoSplit,
  onFitToAudio,
}) {
  const cues = [...(cueTimings ?? [])].sort((a, b) => a.cueOrder - b.cueOrder)
  const pct = (v) => `${Math.max(0, Math.min(100, (v / (duration || 1)) * 100))}%`
  const saveText = SAVE_LABEL[saveStatus]
  const hasAnyAudio = cues.some((c) => (c.items ?? []).some((it) => it.audioDurationSec != null))

  return (
    <section className={styles.cueTiming}>
      <div className={styles.cueTimingHead}>
        <div>
          <div className={styles.detailTitle}>
            자막 타이밍
            {saveText && (
              <span className={`${styles.cueSave} ${saveStatus === 'failed' ? styles.cueSaveFail : ''}`}>
                {' · '}{saveText}
              </span>
            )}
          </div>
          <div className={styles.cueHint}>씬 전체 {duration.toFixed(1)}초 기준으로 cue 시간을 조절합니다.</div>
        </div>
        {cues.length > 0 && hasAnyAudio && (
          <div className={styles.cueHeadBtns}>
            <button type="button" className={styles.cueAutoBtn} onClick={() => onFitToAudio()}>
              음성 길이에 맞추기
            </button>
          </div>
        )}
      </div>

      {cues.length === 0 ? (
        <span className={styles.cueEmpty}>
          이 씬엔 자막 cue가 없습니다. (씬 편집에서 자막을 만들면 여기서 시간을 조절합니다)
        </span>
      ) : (
        <div className={styles.cueList}>
          {cues.map((t) => {
            const active = selectedCue === t.cueOrder
            return (
              <div
                key={t.cueOrder}
                className={`${styles.cueCard} ${active ? styles.cueCardActive : ''}`}
                onClick={() => onSelectCue(active ? null : t.cueOrder)}
              >
                <div className={styles.cueCardTop}>
                  <span className={styles.cueLabel}>씬 {sceneOrder}-{t.cueOrder}</span>
                  {active && <span className={styles.cueShown}>미리보기 표시 중</span>}
                </div>

                <div className={styles.cueFields}>
                  <CueField
                    label="시작"
                    min="0"
                    value={t.startSec}
                    onCommit={(n) => onChange(t.cueOrder, { startSec: n })}
                  />
                  <CueField
                    label="길이"
                    min="0.1"
                    value={t.durationSec}
                    onCommit={(n) => onChange(t.cueOrder, { durationSec: n })}
                  />
                </div>

                {/* 씬 전체 시간 대비 이 cue 구간 위치 */}
                <div className={styles.cueBar} title={`${t.startSec.toFixed(1)}초 ~ ${(t.startSec + t.durationSec).toFixed(1)}초`}>
                  <div
                    className={`${styles.cueSeg} ${active ? styles.cueSegActive : ''}`}
                    style={{ left: pct(t.startSec), width: pct(t.durationSec) }}
                  />
                </div>

                {(() => {
                  const items = t.items ?? []
                  const audioSum = items.reduce((a, it) => a + (it.audioDurationSec || 0), 0)
                  const hasAudio = items.some((it) => it.audioDurationSec != null)
                  return (
                    <div onClick={(e) => e.stopPropagation()}>
                      {/* 자막 길이(cue) vs 음성 합계(items) */}
                      {hasAudio && (
                        <div className={styles.cueLen}>
                          <span>자막 {t.durationSec.toFixed(1)}초</span>
                          <span>음성 합계 {audioSum.toFixed(1)}초</span>
                          {audioSum > t.durationSec + 0.05 && (
                            <span className={styles.cueLenWarn}>음성이 더 깁니다 · 길이 맞추기 권장</span>
                          )}
                        </div>
                      )}

                      {/* cue 안 줄(item)별 음성 */}
                      <div className={styles.cueItems}>
                        {items.map((it) => (
                          <div key={it.sourceItemIndex} className={styles.cueItem}>
                            <div className={styles.cueItemHead}>
                              {it.type === 'narration' ? (
                                <span className={styles.cueItemIcon}>📖</span>
                              ) : it.characterImageUrl ? (
                                <img className={styles.cueItemThumb} src={mediaUrl(it.characterImageUrl)} alt="" draggable={false} />
                              ) : (
                                <span className={styles.cueItemIcon}>🎭</span>
                              )}
                              <span className={styles.cueItemName}>{it.displayName}</span>
                              {it.voiceName && <span className={styles.cueItemVoice}>· {it.voiceName}</span>}
                              {it.audioDurationSec != null && (
                                <span className={styles.cueItemLen}>· 음성 {it.audioDurationSec.toFixed(1)}초</span>
                              )}
                            </div>
                            {it.text && <p className={styles.cueItemText}>{it.text}</p>}
                            {it.ttsStatus === 'ready' && it.audioUrl ? (
                              // eslint-disable-next-line jsx-a11y/media-has-caption
                              <audio className={styles.cueAudioPlayer} controls src={mediaUrl(it.audioUrl)} />
                            ) : (
                              <span className={styles.cueAudioNote}>{TTS_NOTE[it.ttsStatus] ?? TTS_NOTE.none}</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                })()}
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}

import styles from './Timeline.module.css'

export const MIN_DURATION = 1.0
export const MAX_DURATION = 30.0
const STEP = 0.5

export const clampDuration = (v) =>
  Math.min(MAX_DURATION, Math.max(MIN_DURATION, Math.round(v * 10) / 10))

// [-] 3.0초 [+] — 0.5초 단위, 1.0~30.0 clamp. onChange(newDuration) 호출.
export default function DurationControl({ duration, onChange }) {
  const dur = clampDuration(duration ?? 3.0)
  return (
    <div className={styles.duration}>
      <button
        type="button"
        className={styles.durBtn}
        onClick={() => onChange(clampDuration(dur - STEP))}
        disabled={dur <= MIN_DURATION}
        aria-label="길이 줄이기"
      >
        −
      </button>
      <span className={styles.durValue}>{dur.toFixed(1)}초</span>
      <button
        type="button"
        className={styles.durBtn}
        onClick={() => onChange(clampDuration(dur + STEP))}
        disabled={dur >= MAX_DURATION}
        aria-label="길이 늘리기"
      >
        +
      </button>
    </div>
  )
}

// 공통 확인 모달(순수 UI). 어떤 도메인 로직도 없이 props 로만 동작한다.
// open 이 true 일 때만 렌더하고, 오버레이 클릭 / ESC / 취소 버튼으로 onCancel,
// 확인 버튼으로 onConfirm 을 호출한다. variant="danger" 면 확인 버튼이 위험 스타일.
import { useEffect } from 'react'
import { createPortal } from 'react-dom'

import styles from './ConfirmModal.module.css'

export default function ConfirmModal({
  open,
  title,
  message,
  confirmText = '확인',
  cancelText = '취소',
  variant = 'default',
  busy = false,
  onConfirm,
  onCancel,
}) {
  // ESC 로 닫기 (busy 중에는 무시)
  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape' && !busy) onCancel?.()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, busy, onCancel])

  if (!open) return null

  // 카드 등 조상에 transform/filter/backdrop-filter 가 있으면 position:fixed 오버레이가
  // 뷰포트가 아니라 그 조상 기준으로 갇힌다 → body 로 portal 해 항상 전체화면으로 띄운다.
  return createPortal(
    <div
      className={styles.overlay}
      onMouseDown={(e) => {
        // 오버레이 자체를 눌렀을 때만 닫기(모달 내부 클릭은 무시)
        if (e.target === e.currentTarget && !busy) onCancel?.()
      }}
      role="presentation"
    >
      <div className={styles.modal} role="dialog" aria-modal="true" aria-label={title}>
        {title && <h3 className={styles.title}>{title}</h3>}
        {message && <p className={styles.message}>{message}</p>}
        <div className={styles.actions}>
          <button
            type="button"
            className={styles.cancelBtn}
            onClick={() => onCancel?.()}
            disabled={busy}
          >
            {cancelText}
          </button>
          <button
            type="button"
            className={`${styles.confirmBtn} ${variant === 'danger' ? styles.danger : ''}`}
            onClick={() => onConfirm?.()}
            disabled={busy}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}

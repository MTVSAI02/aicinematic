// 🔔 알림 벨: 안읽음 badge + 드롭다운 목록 + 읽음 처리 + 클릭 시 관련 페이지 이동 + 토스트.
// NavBar 에 1개만 마운트(전역). 폴링/상태는 useNotifications 훅이 담당.
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import useNotifications from '@/hooks/useNotifications'
import navBellIcon from '@design/assets/figma-icons/Nav/nav_bell.svg'

import styles from './NotificationBell.module.css'

// 알림 type → 이동할 페이지(완료/실패 모두 같은 작업 페이지로)
const ROUTE_BY_TYPE = {
  character_completed: '/character',
  character_failed: '/character',
  background_completed: '/background',
  background_failed: '/background',
  voice_completed: '/voice',
  voice_failed: '/voice',
  tts_completed: '/timeline',
  tts_failed: '/timeline',
  render_completed: '/render',
  render_failed: '/render',
}

function isFailed(type) {
  return typeof type === 'string' && type.endsWith('_failed')
}

function relativeTime(iso) {
  if (!iso) return ''
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return ''
  const sec = Math.max(0, Math.floor((Date.now() - t) / 1000))
  if (sec < 60) return '방금 전'
  if (sec < 3600) return `${Math.floor(sec / 60)}분 전`
  if (sec < 86400) return `${Math.floor(sec / 3600)}시간 전`
  return `${Math.floor(sec / 86400)}일 전`
}

export default function NotificationBell() {
  const {
    notifications,
    unreadCount,
    permission,
    toasts,
    markRead,
    markAllRead,
    remove,
    clearAll,
    requestPermission,
    dismissToast,
  } = useNotifications()
  const [open, setOpen] = useState(false)
  const wrapRef = useRef(null)
  const navigate = useNavigate()

  // 바깥 클릭/ESC 로 닫기
  useEffect(() => {
    if (!open) return undefined
    const onDown = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false)
    }
    const onKey = (e) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const goTo = (notif) => {
    if (!notif.isRead) markRead(notif.id)
    const route = ROUTE_BY_TYPE[notif.type]
    if (route) navigate(route)
    setOpen(false)
  }

  return (
    <div className={styles.wrap} ref={wrapRef}>
      <button
        type="button"
        className={styles.bell}
        onClick={() => setOpen((v) => !v)}
        aria-label={`알림${unreadCount > 0 ? ` ${unreadCount}건` : ''}`}
      >
        <span className={styles.bellIcon} aria-hidden="true">
          <img src={navBellIcon} alt="알림" className={styles.bellImg} />
        </span>
        {unreadCount > 0 && (
          <span className={styles.badge}>{unreadCount > 99 ? '99+' : unreadCount}</span>
        )}
      </button>

      {open && (
        <div className={styles.dropdown} role="menu">
          <div className={styles.header}>
            <span className={styles.headerTitle}>알림</span>
            <div className={styles.headerActions}>
              {permission === 'default' && (
                <button type="button" className={styles.linkBtn} onClick={requestPermission}>
                  알림 허용하기
                </button>
              )}
              {notifications.length > 0 && (
                <>
                  <button type="button" className={styles.linkBtn} onClick={markAllRead}>
                    모두 읽음
                  </button>
                  <button type="button" className={styles.linkBtn} onClick={clearAll}>
                    전체 삭제
                  </button>
                </>
              )}
            </div>
          </div>

          <ul className={styles.list}>
            {notifications.length === 0 ? (
              <li className={styles.empty}>알림이 없습니다.</li>
            ) : (
              notifications.map((n) => (
                <li key={n.id} className={styles.row}>
                  <button
                    type="button"
                    className={`${styles.item} ${n.isRead ? '' : styles.unread} ${
                      isFailed(n.type) ? styles.fail : ''
                    }`}
                    onClick={() => goTo(n)}
                  >
                    {!n.isRead && <span className={styles.dot} aria-hidden="true" />}
                    <div className={styles.itemBody}>
                      <div className={styles.itemTitle}>{n.title}</div>
                      <div className={styles.itemMsg}>{n.message}</div>
                      <div className={styles.itemTime}>{relativeTime(n.createdAt)}</div>
                    </div>
                  </button>
                  <button
                    type="button"
                    className={styles.delBtn}
                    aria-label="알림 삭제"
                    onClick={() => remove(n.id)}
                  >
                    ×
                  </button>
                </li>
              ))
            )}
          </ul>
        </div>
      )}

      {/* 새 알림 토스트(우상단 고정) */}
      <div className={styles.toasts}>
        {toasts.map((t) => (
          <button
            type="button"
            key={t.id}
            className={`${styles.toast} ${isFailed(t.type) ? styles.toastFail : ''}`}
            onClick={() => {
              dismissToast(t.id)
              goTo(t)
            }}
          >
            <strong className={styles.toastTitle}>{t.title}</strong>
            <span className={styles.toastMsg}>{t.message}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

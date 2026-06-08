// 알림 폴링 + 상태 관리 훅. NavBar 의 NotificationBell 에서 1회만 사용(전역).
// - 5초마다 목록 + 안읽음 개수 폴링
// - 첫 로드의 기존 알림은 토스트/OS알림 안 띄움(seenRef 초기화), 이후 새로 생긴 것만 알림
import { useCallback, useEffect, useRef, useState } from 'react'

import useJobCountStore from '@/store/useJobCountStore'
import {
  deleteAllNotifications,
  deleteNotification,
  getNotifications,
  getUnreadCount,
  markAllNotificationsRead,
  markNotificationRead,
} from '@/api/notifications'
import {
  notifyPermission,
  requestNotifyPermission,
  showOsNotification,
} from '@/utils/browserNotify'
import notifySoundUrl from '@/assets/notify.wav'

const POLL_MS = 5000
const TOAST_MS = 4500

export default function useNotifications() {
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [permission, setPermission] = useState(notifyPermission())
  const [toasts, setToasts] = useState([])
  const seenRef = useRef(null) // Set<id> | null(첫 로드 전)
  const audioRef = useRef(null) // 알림 효과음(지연 생성)

  // 새 알림 효과음 재생. autoplay 정책상 사용자 상호작용 전엔 막힐 수 있어 조용히 무시.
  const playSound = useCallback(() => {
    try {
      if (!audioRef.current) audioRef.current = new Audio(notifySoundUrl)
      audioRef.current.currentTime = 0
      audioRef.current.play().catch(() => {})
    } catch {
      /* noop */
    }
  }, [])

  const dismissToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const pushToast = useCallback(
    (n) => {
      setToasts((prev) => [...prev, n])
      setTimeout(() => dismissToast(n.id), TOAST_MS)
    },
    [dismissToast],
  )

  const refresh = useCallback(
    async (signal) => {
      try {
        const [list, count] = await Promise.all([
          getNotifications(50, { signal }),
          getUnreadCount({ signal }),
        ])
        const items = Array.isArray(list) ? list : []
        setNotifications(items)
        setUnreadCount(count?.count ?? 0)

        // 새 알림 감지(첫 로드는 기존 전부 seen 처리 → 알림 안 띄움)
        if (seenRef.current === null) {
          seenRef.current = new Set(items.map((n) => n.id))
        } else {
          const fresh = items.filter((n) => !seenRef.current.has(n.id))
          if (fresh.length > 0) playSound() // OS 알림과 함께 효과음(배치당 1회)
          fresh.forEach((n) => {
            seenRef.current.add(n.id)
            pushToast(n)
            showOsNotification(n.title, n.message)
          })
        }
      } catch {
        // 폴링 실패(백엔드 미가동/네트워크)는 조용히 무시
      }
    },
    [pushToast, playSound],
  )

  const activeJobCount = useJobCountStore((s) => s.activeJobCount)

  useEffect(() => {
    if (activeJobCount === 0) return
    const ctrl = new AbortController()
    // refresh 의 setState 는 전부 await(fetch) 이후라 동기 cascading render 가 아니다.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh(ctrl.signal)
    const id = setInterval(() => refresh(ctrl.signal), POLL_MS)
    return () => {
      ctrl.abort()
      clearInterval(id)
    }
  }, [refresh, activeJobCount])

  const markRead = useCallback(
    async (id) => {
      try {
        await markNotificationRead(id)
      } catch {
        /* noop */
      }
      refresh()
    },
    [refresh],
  )

  const markAllRead = useCallback(async () => {
    try {
      await markAllNotificationsRead()
    } catch {
      /* noop */
    }
    refresh()
  }, [refresh])

  const remove = useCallback(
    async (id) => {
      // 낙관적 제거 후 서버 반영(실패해도 다음 폴링이 보정)
      setNotifications((prev) => prev.filter((n) => n.id !== id))
      try {
        await deleteNotification(id)
      } catch {
        /* noop */
      }
      refresh()
    },
    [refresh],
  )

  const clearAll = useCallback(async () => {
    setNotifications([])
    try {
      await deleteAllNotifications()
    } catch {
      /* noop */
    }
    refresh()
  }, [refresh])

  const requestPermission = useCallback(async () => {
    const p = await requestNotifyPermission()
    setPermission(p)
  }, [])

  return {
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
  }
}

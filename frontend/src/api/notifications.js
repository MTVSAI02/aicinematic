// 백엔드 알림 API. job 완료/실패 알림을 폴링 조회하고 읽음 처리한다.
import { request } from '@/utils/request'

// GET /api/notifications?limit= — 최신 알림 목록(읽음 포함)
export function getNotifications(limit = 50, { signal } = {}) {
  return request(`/api/notifications?limit=${limit}`, { signal })
}

// GET /api/notifications/unread-count — 안 읽은 개수 { count }
export function getUnreadCount({ signal } = {}) {
  return request('/api/notifications/unread-count', { signal })
}

// PATCH /api/notifications/{id}/read — 하나 읽음 처리
export function markNotificationRead(id) {
  return request(`/api/notifications/${id}/read`, { method: 'PATCH' })
}

// PATCH /api/notifications/read-all — 전부 읽음 처리 { updated }
export function markAllNotificationsRead() {
  return request('/api/notifications/read-all', { method: 'PATCH' })
}

// DELETE /api/notifications/{id} — 하나 삭제(204)
export function deleteNotification(id) {
  return request(`/api/notifications/${id}`, { method: 'DELETE' })
}

// DELETE /api/notifications — 전체 삭제 { deleted }
export function deleteAllNotifications() {
  return request('/api/notifications', { method: 'DELETE' })
}

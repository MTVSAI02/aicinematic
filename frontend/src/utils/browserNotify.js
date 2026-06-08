// 브라우저 Notification API 래퍼. 탭이 열려 있는 동안 OS 알림을 띄운다.
// 권한은 사용자가 명시적으로 요청(버튼)할 때만 묻는다 — 자동 요청 금지(브라우저 권장).

// 'granted' | 'denied' | 'default' | 'unsupported'
export function notifyPermission() {
  if (typeof Notification === 'undefined') return 'unsupported'
  return Notification.permission
}

export async function requestNotifyPermission() {
  if (typeof Notification === 'undefined') return 'unsupported'
  try {
    return await Notification.requestPermission()
  } catch {
    return Notification.permission
  }
}

export function showOsNotification(title, body) {
  if (typeof Notification === 'undefined' || Notification.permission !== 'granted') return
  try {
    new Notification(title, { body: body || '' })
  } catch {
    // 일부 브라우저/시크릿 모드에서 throw — 무시
  }
}

/**
 * 桌面通知工具
 * 优先使用 Electron Notification API，回退到 Web Notification
 */

export function sendNotification(title: string, body: string) {
  // Electron 环境
  if (window.electronAPI?.sendNotification) {
    window.electronAPI.sendNotification(title, body)
    return
  }

  // Web Notification
  if ('Notification' in window) {
    if (Notification.permission === 'granted') {
      new Notification(title, { body })
    } else if (Notification.permission !== 'denied') {
      Notification.requestPermission().then((permission) => {
        if (permission === 'granted') {
          new Notification(title, { body })
        }
      })
    }
  }
}
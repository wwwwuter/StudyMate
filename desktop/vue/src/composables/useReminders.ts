import { onMounted, onBeforeUnmount } from 'vue'
import { getPendingReminders, ackReminders, type ReminderItem } from '@/api/reminder'

const POLL_MS = 20_000
let timer: number | null = null
// 会话内已弹过的提醒，避免重复打扰（后端 delivered 标记是兜底）
const shown = new Set<number>()

function requestPermission() {
  if (typeof window === 'undefined' || !('Notification' in window)) return
  if (Notification.permission === 'default') {
    Notification.requestPermission().catch(() => {})
  }
}

async function poll() {
  if (typeof window === 'undefined' || !('Notification' in window)) return
  if (Notification.permission !== 'granted') return
  try {
    const res = await getPendingReminders()
    const items: ReminderItem[] = res.data || []
    if (!items.length) return
    const toAck: number[] = []
    for (const it of items) {
      // 已展示过但后端尚未确认：继续回执，不重复弹窗
      if (shown.has(it.id)) {
        toAck.push(it.id)
        continue
      }
      shown.add(it.id)
      const when = it.fire_at ? it.fire_at.slice(11) : ''
      const n = new Notification('📚 学习任务提醒', {
        body: `${it.subject} · ${it.content}${when ? `（${when} 开始）` : ''}`,
      })
      n.onclick = () => {
        window.focus()
        n.close()
      }
      toAck.push(it.id)
    }
    if (toAck.length) await ackReminders(toAck).catch(() => {})
  } catch {
    // 瞬时错误忽略，下次轮询重试
  }
}

/** 在 App 根组件挂载一次：请求通知权限、周期轮询并弹出系统通知。 */
export function useReminders() {
  onMounted(() => {
    requestPermission()
    poll()
    timer = window.setInterval(poll, POLL_MS)
  })
  onBeforeUnmount(() => {
    if (timer !== null) {
      clearInterval(timer)
      timer = null
    }
  })
}

import { onMounted, onBeforeUnmount } from 'vue'
import {
  getPendingReminders,
  ackReminders,
  type ReminderItem,
} from '@/api/reminder'
import { listTasks, type TaskItem } from '@/api/task'
import { startTimer, getTimerCurrent } from '@/api/plan'

/** 轮询间隔：15 秒。前端轻量轮询，后台 APScheduler 负责生成提醒。 */
const POLL_MS = 15_000
/** 计划到点后，自动开启计时的窗口（秒）。错过该窗口不再补开，避免误开旧计划。 */
const AUTOSTART_WINDOW = 5 * 60

let timer: number | null = null
// 会话内已通知过的提醒，避免重复弹窗
const shown = new Set<number>()
// 会话内已触发过自动计时的计划，避免重复开启
const autoStarted = new Set<number>()

function todayStr(): string {
  const d = new Date()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

function hmToSec(hhmm: string): number {
  const [h, m] = hhmm.split(':').map(Number)
  return (h || 0) * 3600 + (m || 0) * 60
}

/** 请求浏览器通知权限（仅在 Web 下；桌面端走 electronAPI，无需此项）。 */
export function ensureNotifyPermission() {
  if (typeof window === 'undefined' || !('Notification' in window)) return
  if (Notification.permission === 'default') {
    Notification.requestPermission().catch(() => {})
  }
}

/** 弹出系统通知：优先 electronAPI（桌面 OS 通知），降级到浏览器 Notification。 */
function notify(item: ReminderItem) {
  const title = '⏰ 学习计划提醒'
  const when = item.fire_at ? item.fire_at.slice(11, 16) : ''
  const body = `${item.subject} · ${item.content}${when ? `（${when} 开始）` : ''}`

  const api = (window as any).electronAPI
  if (api?.showNotification) {
    api.showNotification({ title, body })
    return
  }
  if (typeof window !== 'undefined' && 'Notification' in window) {
    if (Notification.permission === 'granted') {
      const n = new Notification(title, { body })
      n.onclick = () => {
        window.focus()
        n.close()
      }
    } else if (Notification.permission === 'default') {
      Notification.requestPermission()
        .then((p) => {
          if (p === 'granted') new Notification(title, { body })
        })
        .catch(() => {})
    }
  }
}

/** 拉取未送达提醒并弹通知，随后回执。 */
async function notifyReminders() {
  try {
    const res = await getPendingReminders()
    const items: ReminderItem[] = res.data || []
    if (!items.length) return
    const toAck: number[] = []
    for (const it of items) {
      if (!shown.has(it.id)) {
        shown.add(it.id)
        notify(it)
      }
      toAck.push(it.id)
    }
    if (toAck.length) await ackReminders(toAck).catch(() => {})
  } catch {
    /* 瞬时错误忽略，下次轮询重试 */
  }
}

/** 计划到点自动开启计时：扫描今日待开始计划，命中时间窗且无进行中计时则开启。 */
async function autoStart() {
  try {
    const res = await listTasks({ date: todayStr(), status: 'pending' })
    const tasks: TaskItem[] = (res.data || []).filter((t) => t.status === 'pending')
    if (!tasks.length) return
    const now = new Date()
    const nowSec = hmToSec(now.toTimeString().slice(0, 5))
    for (const t of tasks) {
      if (!t.start_time || autoStarted.has(t.id)) continue
      const startSec = hmToSec(t.start_time)
      if (nowSec >= startSec && nowSec <= startSec + AUTOSTART_WINDOW) {
        autoStarted.add(t.id)
        // 不打断正在进行的计时
        const cur = await getTimerCurrent().catch(() => ({ data: null }))
        if (cur.data) continue
        await startTimer({ task_id: t.id }).catch(() => {})
      }
    }
  } catch {
    /* 瞬时错误忽略 */
  }
}

async function poll() {
  await notifyReminders()
  await autoStart()
}

/**
 * 在 App 根组件挂载一次：请求通知权限、周期轮询提醒 + 自动计时。
 */
export function useScheduler() {
  onMounted(() => {
    ensureNotifyPermission()
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

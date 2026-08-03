import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  startTimer,
  stopTimer,
  syncPomodoroPhase,
  reportPomodoroCycle,
  type TimerSessionItem,
} from '@/api/plan'
import type { TaskItem } from '@/api/task'
import { getBootstrap } from '@/api/bootstrap'

export type TimerMode = 'task' | 'pomodoro' | 'countdown' | 'free'

function parseMs(iso?: string | null): number {
  if (!iso) return NaN
  const ms = new Date(iso).getTime()
  return Number.isNaN(ms) ? NaN : ms
}

function fmt(s: number): string {
  s = Math.max(0, Math.floor(s))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  const mm = String(m).padStart(2, '0')
  const ss = String(sec).padStart(2, '0')
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`
}

/**
 * 全局计时 Store（Phase 6-3）：
 * 计时状态从 TimerView 页面级提升为全局，App 启动 hydrate 一次，
 * 刷新/切页/重启后由后端权威字段重建，所有页面共享同一计时视图。
 */
export const useTimerStore = defineStore('timer', () => {
  // ---- 会话（后端权威）----
  const session = ref<TimerSessionItem | null>(null)
  const hydrated = ref(false)
  // 全局时钟：任何组件每秒调 tick() 推进（计时页 + 顶栏）
  const now = ref(Date.now())

  // ---- 番茄钟运行参数（切段同步用）----
  const workSec = ref(25 * 60)
  const breakSec = ref(5 * 60)
  const pomoCycle = ref(1)

  // ---- 计划计时 ----
  const taskOverNotified = ref(false)
  const extraStartAt = ref<number | null>(null)

  const mode = computed<TimerMode>(() => {
    if (!session.value) return 'task'
    return session.value.mode === 'countup' ? 'free' : (session.value.mode as TimerMode)
  })
  const running = computed(() => !!session.value)

  /** 番茄钟当前阶段（刷新后由后端 pomodoro_phase 重建）。 */
  const pomoPhase = computed<'work' | 'break'>(() => {
    if (session.value?.mode === 'pomodoro' && session.value.pomodoro_phase) {
      return session.value.pomodoro_phase
    }
    return 'work'
  })

  // ---- 派生：通用已计时 ----
  const elapsedSec = computed(() => {
    const start = parseMs(session.value?.started_at)
    if (Number.isNaN(start)) return 0
    return Math.max(0, Math.floor((now.value - start) / 1000))
  })

  // ---- 派生：计划计时（task 模式倒计时 + 超时额外学习）----
  const planEndMs = computed(() => parseMs(session.value?.plan_end_time))
  const planStartMs = computed(() => parseMs(session.value?.plan_start_time))
  const taskLeft = computed(() => {
    if (mode.value !== 'task' || Number.isNaN(planEndMs.value)) return 0
    return Math.max(0, Math.floor((planEndMs.value - now.value) / 1000))
  })
  const taskOver = computed(() => {
    if (mode.value !== 'task' || Number.isNaN(planEndMs.value)) return false
    return now.value > planEndMs.value
  })
  const extraSec = computed(() => {
    if (!extraStartAt.value) return 0
    return Math.max(0, Math.floor((now.value - extraStartAt.value) / 1000))
  })
  const taskEarlyMin = computed(() => {
    if (mode.value !== 'task' || Number.isNaN(planStartMs.value)) return 0
    const actual = parseMs(session.value?.started_at)
    if (Number.isNaN(actual)) return 0
    return Math.max(0, Math.round((planStartMs.value - actual) / 60000))
  })

  // ---- 派生：番茄钟剩余（由后端 phase_started_at + target_seconds 重建）----
  const pomoLeft = computed(() => {
    if (mode.value !== 'pomodoro' || !session.value) return 0
    const target = session.value.target_seconds ?? 0
    const phaseStart = parseMs(session.value.phase_started_at)
    if (!target || Number.isNaN(phaseStart)) return 0
    return Math.max(0, target - Math.floor((now.value - phaseStart) / 1000))
  })

  // ---- 派生：倒计时剩余（由后端 target_seconds 重建）----
  const countdownLeft = computed(() => {
    if (mode.value !== 'countdown' || !session.value) return 0
    const target = session.value.target_seconds ?? 0
    const start = parseMs(session.value.started_at)
    if (!target || Number.isNaN(start)) return 0
    return Math.max(0, target - Math.floor((now.value - start) / 1000))
  })

  function fmtClock(iso?: string | null): string {
    const d = new Date(parseMs(iso))
    if (Number.isNaN(d.getTime())) return ''
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
  }

  // ---- 派生：主时钟 + 副标题（计时页与顶栏共用）----
  const clockText = computed(() => {
    if (mode.value === 'pomodoro' && session.value) return fmt(pomoLeft.value)
    if (mode.value === 'countdown' && session.value) return fmt(countdownLeft.value)
    if (mode.value === 'task' && !Number.isNaN(planEndMs.value)) {
      return taskOver.value ? fmt(extraSec.value) : fmt(taskLeft.value)
    }
    if (session.value) return fmt(elapsedSec.value)
    return '00:00'
  })

  const runSubText = computed(() => {
    if (!session.value) return ''
    if (mode.value === 'pomodoro') {
      return `${pomoPhase.value === 'work' ? '专注剩余' : '休息剩余'} · 第 ${pomoCycle.value} 轮`
    }
    if (mode.value === 'countdown') return '倒计时剩余'
    if (mode.value === 'task') {
      const task = session.value.task
      const span =
        session.value.plan_start_time && session.value.plan_end_time
          ? `${fmtClock(session.value.plan_start_time)}-${fmtClock(session.value.plan_end_time)}`
          : ''
      const early = taskEarlyMin.value > 0 ? `· 提前 ${taskEarlyMin.value} 分钟开始` : ''
      let state = ''
      if (taskOver.value) {
        const over = Number.isNaN(planEndMs.value)
          ? 0
          : Math.max(0, Math.floor((now.value - planEndMs.value) / 1000))
        state = `· 计划结束 · 已超出 ${fmt(over)} · 额外学习 ${fmt(extraSec.value)}`
      } else {
        state = `· 剩余 ${fmt(taskLeft.value)}`
      }
      return `${task?.content || ''} ${span} ${state} ${early}`.trim()
    }
    return '已计时'
  })

  /** 顶栏摘要：如「正在学习 数学强化 · 剩余 02:18:00」。 */
  const summary = computed(() => {
    if (!session.value) return null
    let label = ''
    if (mode.value === 'task') label = session.value.task?.content || '计划计时'
    else if (mode.value === 'pomodoro') label = `番茄钟 ${pomoPhase.value === 'work' ? '专注' : '休息'}`
    else if (mode.value === 'countdown') label = '倒计时'
    else label = session.value.note || '自由计时'
    return { label, clock: clockText.value, sub: runSubText.value }
  })

  // ---- 会话装载（hydrate / 新会话共用）----
  function applySession(s: TimerSessionItem | null) {
    session.value = s
    pomoCycle.value = 1
    taskOverNotified.value = false
    extraStartAt.value = null
  }

  /** App 启动水合：从 /system/bootstrap 恢复（后端权威，含番茄段/倒计时目标）。 */
  async function hydrate() {
    try {
      const data = await getBootstrap()
      if (data.user.authenticated) applySession(data.timer)
      else session.value = null
    } catch {
      session.value = null
    } finally {
      hydrated.value = true
    }
  }

  // ---- 开始计时（统一入口）----
  async function startTask(t: TaskItem) {
    try {
      const res = await startTimer({ mode: 'task', task_id: t.id })
      applySession(res.data)
    } catch (e: any) {
      ElMessage.error(e?.message || '开始计时失败')
      throw e
    }
  }

  async function startPomodoro(workMin: number, breakMin: number) {
    workSec.value = workMin * 60
    breakSec.value = breakMin * 60
    try {
      const res = await startTimer({ mode: 'pomodoro', duration: workSec.value })
      applySession(res.data)
      // 后端已置 phase=work + phase_started_at=now，前端无需维护递减
    } catch (e: any) {
      ElMessage.error(e?.message || '开始失败')
      throw e
    }
  }

  async function startCountdown(minutes: number, taskId?: number | null) {
    const payload: { mode: 'countdown'; duration: number; task_id?: number } = {
      mode: 'countdown',
      duration: minutes * 60,
    }
    if (taskId) payload.task_id = taskId
    try {
      const res = await startTimer(payload)
      applySession(res.data)
    } catch (e: any) {
      ElMessage.error(e?.message || '开始失败')
      throw e
    }
  }

  async function startFree(note?: string) {
    try {
      const res = await startTimer({ mode: 'countup', note: note || undefined })
      applySession(res.data)
    } catch (e: any) {
      ElMessage.error(e?.message || '开始失败')
      throw e
    }
  }

  /** 专注段结束：上报本轮 + 切到休息段（后端同步，供刷新重建）。 */
  async function reportCycle() {
    const s = session.value
    if (!s) return
    try {
      await reportPomodoroCycle({
        session_id: s.id,
        cycle_number: pomoCycle.value,
        focus_duration: workSec.value,
        break_duration: breakSec.value,
      })
      await syncPomodoroPhase({ phase: 'break', target_seconds: breakSec.value })
      pomoCycle.value += 1
    } catch {
      /* 上报失败不阻断；统计回退整段时长 */
    }
  }

  /** 计划超时弹窗：点「继续学习」——额外学习从此刻起算（从 0 累加）。 */
  function continueOvertime() {
    extraStartAt.value = Date.now()
  }

  async function stop(silent = false) {
    try {
      await stopTimer({})
    } catch (e: any) {
      if (!silent) ElMessage.error(e?.message || '结束失败')
    }
    session.value = null
    extraStartAt.value = null
    taskOverNotified.value = false
  }

  /** 每秒推进：更新时钟 + 处理番茄/倒计时归零 + 计划超时提示（全局唯一 tick）。 */
  function tick() {
    now.value = Date.now()
    const s = session.value
    if (!s) return
    if (mode.value === 'pomodoro') {
      if (pomoLeft.value <= 0) {
        if (pomoPhase.value === 'work') {
          // 专注结束 → 上报本轮并进入休息
          reportCycle()
        } else {
          // 休息结束 → 一轮完成，自动保存
          stop(true)
        }
      }
    } else if (mode.value === 'countdown') {
      if (countdownLeft.value <= 0) stop(true)
    } else if (mode.value === 'task' && taskOver.value && !taskOverNotified.value) {
      taskOverNotified.value = true
      ElMessageBox.confirm(
        '计划时间已结束，是否继续学习？（继续将记录为额外学习时间）',
        '计划结束',
        { type: 'warning', confirmButtonText: '继续学习', cancelButtonText: '结束并保存' },
      )
        .then(() => continueOvertime())
        .catch(() => stop(false))
    }
  }

  return {
    session,
    hydrated,
    now,
    mode,
    running,
    pomoPhase,
    pomoCycle,
    elapsedSec,
    taskLeft,
    taskOver,
    taskEarlyMin,
    extraSec,
    pomoLeft,
    countdownLeft,
    clockText,
    runSubText,
    summary,
    hydrate,
    applySession,
    startTask,
    startPomodoro,
    startCountdown,
    startFree,
    reportCycle,
    continueOvertime,
    stop,
    tick,
  }
})

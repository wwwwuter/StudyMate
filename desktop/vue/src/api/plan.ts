import request from './request'

/** 一条由 AI / 规则识别出的计划（时间槽）。 */
export interface PlanItem {
  date: string | null
  subject: string
  content: string
  start_time: string | null
  end_time: string | null
  needs_review?: boolean
  priority?: number
}

/** 解析上传的计划（文本 / 文件），返回可编辑的计划列表（不落库）。 */
export const parsePlan = (form: FormData) =>
  request
    .post('/plans/parse', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120_000, // AI 视觉/文档解析较慢，单独延长
    })
    .then(
      (r) =>
        r.data as {
          code: number
          message?: string
          data: { plans: PlanItem[]; plan_name?: string | null }
        },
    )

/** 确认结果：StudyPlan 版本 + 落库/冲突信息。 */
export interface ConfirmResult {
  plan_id: number
  plan_name: string
  version: number
  created: number
  skipped: {
    date: string
    subject: string
    content: string
    start_time?: string
    end_time?: string
    conflicts_with: unknown[]
  }[]
}

/** 确认计划：生成 StudyPlan 版本并落库（冲突任务由后端跳过并返回）。 */
export const confirmPlans = (payload: { plan_name?: string; tasks: PlanItem[] }) =>
  request
    .post('/plans/confirm', payload)
    .then((r) => r.data as { code: number; message?: string; data: ConfirmResult })

/** 运行中的计时会话（含关联计划）。 */
export interface TimerSessionItem {
  id: number
  user_id: number
  task_id: number | null
  mode: 'pomodoro' | 'task' | 'countup' | 'countdown'
  started_at: string
  ended_at: string | null
  plan_start_time?: string | null
  plan_end_time?: string | null
  duration_seconds: number | null
  status: 'running' | 'done' | 'cancelled'
  note: string | null
  task: {
    id: number
    subject: string
    content: string
    start_time: string | null
    end_time: string | null
    status: string
  } | null
}

/** 开启一次计时。会先结束当前运行中的会话。 */
export const startTimer = (payload: {
  task_id?: number
  mode?: TimerSessionItem['mode']
  note?: string
  duration?: number
}) =>
  request
    .post('/plans/timer/start', payload)
    .then((r) => r.data as { code: number; message?: string; data: TimerSessionItem })

/** 记录番茄钟一轮（专注 + 休息），仅番茄钟会话调用。 */
export const reportPomodoroCycle = (payload: {
  session_id: number
  cycle_number?: number
  focus_duration: number
  break_duration?: number
}) =>
  request
    .post('/plans/timer/cycle', payload)
    .then((r) => r.data as { code: number; message?: string; data: { cycle_number: number } })

/** 结束计时（缺省结束当前运行中的会话）。 */
export const stopTimer = (payload: { session_id?: number }) =>
  request
    .post('/plans/timer/stop', payload)
    .then((r) => r.data as { code: number; message?: string; data: TimerSessionItem })

/** 返回当前运行中的计时会话，无则返回 { data: null }。 */
export const getTimerCurrent = () =>
  request
    .get('/plans/timer/current')
    .then((r) => r.data as { code: number; data: TimerSessionItem | null })

/** 学习统计（按范围聚合计时时长 / 次数 / 科目占比 / 每日趋势 + 任务完成率）。 */
export interface PlanStats {
  range: string
  total_seconds: number
  total_hours: number
  session_count: number
  by_subject: Record<string, number>
  daily: { date: string; seconds: number }[]
  task_total: number
  task_done: number
  completion_rate: number
}

export const getPlanStats = (range: 'day' | 'week' | 'month' | 'all' = 'day') =>
  request
    .get('/plans/stats', { params: { range } })
    .then((r) => r.data as { code: number; data: PlanStats })

import request from './request'

/** 科目学习占比项；time 为秒。 */
export interface StatSubject {
  name: string
  time: number
}

/** 今日任务项。 */
export interface TodayTaskItem {
  id: number
  subject: string
  content: string
  start_time: string | null
  end_time: string | null
  status: 'pending' | 'doing' | 'done' | 'overdue'
}

/** 趋势点；time 为秒。 */
export interface TrendPoint {
  date: string
  time: number
}

/** 计时模式占比项；value 为秒，count 为该模式次数。 */
export interface ModeItem {
  name: string
  mode: string
  value: number
  count: number
}

/** 今日统计。 */
export interface TodayStat {
  date: string
  study_time: number
  task_total: number
  task_completed: number
  completion_rate: number
  current_task: TodayTaskItem | null
  subjects: StatSubject[]
  tasks: TodayTaskItem[]
  // 计时模式维度
  pomodoro_time: number
  task_time: number
  free_time: number
  sessions: {
    pomodoro: number
    task: number
    countup: number
    countdown: number
  }
}

/** 计划版本执行情况（Phase 6）。 */
export interface PlanStatItem {
  plan_id: number
  plan_name: string
  version: number
  total: number
  done: number
  rate: number
}

/** 全部统计。 */
export interface AllStat {
  total_time: number
  total_sessions: number
  completed_tasks: number
  completion_rate: number
  plan_execution_rate: number
  plan_stats: PlanStatItem[]
  continuous_days: number
  trend: TrendPoint[]
  subjects: StatSubject[]
  // 计时模式维度
  pomodoro_total: number
  task_total: number
  countup_total: number
  countdown_total: number
  mode_distribution: ModeItem[]
}

/** 今日学习执行情况。 */
export const getTodayStat = () =>
  request.get('/stat/today').then((r) => r.data as { code: number; data: TodayStat })

/** 长期学习情况统计。 */
export const getAllStat = () =>
  request.get('/stat/all').then((r) => r.data as { code: number; data: AllStat })

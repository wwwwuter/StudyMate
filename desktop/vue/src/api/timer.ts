import request from './request'

export type TimerMode = 'pomodoro' | 'countup' | 'countdown' | 'focus'

export interface RecordItem {
  id: number
  task_id: number | null
  start_time: string
  end_time: string | null
  duration: number
  mode: TimerMode
  subject: string | null
  planned_duration: number | null
  note: string | null
  create_time: string
}

export interface StatsData {
  range: string
  total_seconds: number
  total_hours: number
  session_count: number
  by_mode: Record<string, number>
  by_subject: Record<string, number>
  daily: { date: string; seconds: number }[]
}

export const startRecord = (payload: {
  mode: TimerMode
  subject?: string | null
  task_id?: number | null
  planned_duration?: number | null
  note?: string | null
}) => request.post('/records', payload).then((r) => r.data.data as RecordItem)

export const stopRecord = (id: number) =>
  request.put(`/records/${id}/stop`).then((r) => r.data.data as RecordItem)

export const deleteRecord = (id: number) =>
  request.delete(`/records/${id}`).then((r) => r.data)

export const getHistory = (params: {
  mode?: string
  subject?: string
  date?: string
  page?: number
  page_size?: number
}) => request.get('/records/history', { params }).then((r) => r.data as {
  code: number
  data: RecordItem[]
  total: number
  page: number
  page_size: number
})

export const getStats = (range: 'day' | 'week' | 'month' | 'all' = 'week') =>
  request.get('/records/stats', { params: { range } }).then((r) => r.data.data as StatsData)

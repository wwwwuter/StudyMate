import request from './request'

export interface TaskItem {
  id: number
  user_id: number
  date: string
  subject: string
  content: string
  start_time: string | null
  end_time: string | null
  status: 'pending' | 'done' | 'cancelled'
  plan_source: 'manual' | 'excel' | 'json' | 'pdf' | 'auto' | 'parsed'
  priority?: number
  estimated_minutes?: number | null
  tags?: string | null
  review_round?: number
  root_task_id?: number | null
  create_time: string
  update_time: string
}

export interface TaskFilters {
  date?: string
  start_date?: string
  end_date?: string
  subject?: string
  status?: string
  keyword?: string
  page?: number
  page_size?: number
}

export interface DailyStats {
  date: string
  total: number
  done: number
  completion_rate: number
  subjects: string[]
}

export const listTasks = (filters: TaskFilters = {}) =>
  request
    .get('/tasks', { params: filters })
    .then((r) => r.data as { code: number; data: TaskItem[]; total: number })

export const getTask = (id: number) =>
  request.get(`/tasks/${id}`).then((r) => r.data.data as TaskItem)

export const createTask = (payload: Partial<TaskItem>) =>
  request.post('/tasks', payload).then((r) => r.data.data as TaskItem)

export const updateTask = (id: number, payload: Partial<TaskItem>) =>
  request.put(`/tasks/${id}`, payload).then((r) => r.data.data as TaskItem)

export const deleteTask = (id: number) =>
  request.delete(`/tasks/${id}`).then((r) => r.data)

export const batchDeleteTasks = (ids: number[]) =>
  request.delete('/tasks/batch', { data: { ids } }).then((r) => r.data)

export interface DeleteCriteria {
  subject?: string
  start_date?: string
  end_date?: string
  start_time?: string
  end_time?: string
  status?: string
  plan_source?: string
}

export const previewDeleteByCriteria = (criteria: DeleteCriteria) =>
  request
    .post('/tasks/delete-by-criteria/preview', criteria)
    .then((r) => r.data.data as { count: number })

export const deleteTasksByCriteria = (criteria: DeleteCriteria) =>
  request
    .post('/tasks/delete-by-criteria', criteria)
    .then((r) => r.data.data as { deleted: number })

export const batchCreate = (items: Partial<TaskItem>[]) =>
  request.post('/tasks/batch', items).then((r) => r.data)

export const dailyStats = (date: string) =>
  request.get('/tasks/stats/daily', { params: { date } }).then((r) => r.data.data as DailyStats)


// ---- 智能排程（M2）：艾宾浩斯间隔重复 ----
export interface ScheduleResult {
  count: number
  skipped: number
  intervals: number[]
  tasks: TaskItem[]
}

export const generateSchedule = (items: { subject: string; content: string; priority?: number }[], studyDate?: string) =>
  request
    .post('/schedule/generate', { items, study_date: studyDate })
    .then((r) => r.data as { code: number; message?: string; data: ScheduleResult })

export const getReviewChain = (rootTaskId: number) =>
  request
    .get(`/schedule/chain/${rootTaskId}`)
    .then((r) => r.data as { code: number; data: { root_task_id: number; tasks: TaskItem[] } })

export interface UpcomingTask extends TaskItem {
  round_label: string
}

export const getUpcomingReviews = (start: string, end: string) =>
  request
    .get('/schedule/upcoming', { params: { start, end } })
    .then((r) => r.data as { code: number; data: { start: string; end: string; count: number; tasks: UpcomingTask[] } })

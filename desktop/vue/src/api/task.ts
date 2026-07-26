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
  plan_source: 'manual' | 'excel' | 'json' | 'pdf' | 'auto'
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

export const batchCreate = (items: Partial<TaskItem>[]) =>
  request.post('/tasks/batch', items).then((r) => r.data)

export const importTasks = (type: 'excel' | 'json' | 'pdf', file: File, fileName: string) => {
  const form = new FormData()
  form.append('file', file, fileName)
  return request
    .post(`/tasks/import/${type}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data)
}

export const dailyStats = (date: string) =>
  request.get('/tasks/stats/daily', { params: { date } }).then((r) => r.data.data as DailyStats)

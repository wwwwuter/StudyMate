import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器：添加 JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('studymate_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：处理错误
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('studymate_token')
      window.location.hash = '#/login'
    }
    return Promise.reject(error)
  },
)

export default api

// 用户相关 API
export const userApi = {
  login(code: string) {
    return api.post('/auth/wechat', { code })
  },
  getInfo() {
    return api.get('/user/info')
  },
  logout() {
    return api.post('/auth/logout')
  },
}

// 任务相关 API
export const taskApi = {
  getTasks(date?: string) {
    const params = date ? { date } : {}
    return api.get('/tasks', { params })
  },
  createTask(data: any) {
    return api.post('/tasks', data)
  },
  updateTask(id: number, data: any) {
    return api.put(`/tasks/${id}`, data)
  },
  deleteTask(id: number) {
    return api.delete(`/tasks/${id}`)
  },
  importExcel(file: File) {
    const form = new FormData()
    form.append('file', file)
    return api.post('/tasks/import/excel', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  importJson(file: File) {
    const form = new FormData()
    form.append('file', file)
    return api.post('/tasks/import/json', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  importPdf(file: File) {
    const form = new FormData()
    form.append('file', file)
    return api.post('/tasks/import/pdf', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  dailyStats(date?: string) {
    const params = date ? { date } : {}
    return api.get('/tasks/stats/daily', { params })
  },
}

// 记录相关 API
export const recordApi = {
  startRecord(data: any) {
    return api.post('/records', data)
  },
  stopRecord(id: number) {
    return api.put(`/records/${id}/stop`)
  },
  getHistory(date?: string) {
    const params = date ? { date } : {}
    return api.get('/records/history', { params })
  },
  weeklyStats() {
    return api.get('/records/stats/weekly')
  },
}

// AI 相关 API
export const aiApi = {
  dailySummary(date?: string) {
    return api.post('/ai/daily-summary', { date })
  },
  planOptimize() {
    return api.post('/ai/plan-optimize')
  },
  chat(message: string) {
    return api.post('/ai/chat', { message })
  },
}
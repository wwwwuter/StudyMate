import axios from 'axios'

// 全局 axios 实例：所有后端请求统一走 /api 前缀（由 vite dev proxy 转发到 Flask:5000）
const request = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

// 请求拦截：注入 Bearer 令牌
request.interceptors.request.use((config) => {
  const token = localStorage.getItem('sm_access_token')
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`)
  }
  return config
})

// 响应拦截：统一处理业务码与 401
request.interceptors.response.use(
  (resp) => {
    const body = resp.data
    if (body && typeof body.code === 'number' && body.code !== 200) {
      if (body.code === 401) {
        clearToken()
      }
      return Promise.reject(new Error(body.message || '请求失败'))
    }
    return resp
  },
  (error) => {
    const status = error.response?.status
    const body = error.response?.data
    if (status === 401) {
      clearToken()
    }
    const msg =
      (body && (body.message || body.detail)) ||
      error.message ||
      '网络异常'
    return Promise.reject(new Error(msg))
  },
)

function clearToken() {
  localStorage.removeItem('sm_access_token')
  localStorage.removeItem('sm_refresh_token')
  localStorage.removeItem('sm_user')
}

export default request

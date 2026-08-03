import request from './request'
import type { TimerSessionItem } from './plan'

/**
 * 应用启动聚合状态（对应后端 GET /api/system/bootstrap）。
 * 一次请求返回 user + timer + reminder，供三个 store 水合共享，
 * 避免启动时多次往返导致页面闪跳。
 */
export interface BootstrapData {
  user: {
    setup_done: boolean
    authenticated: boolean
    id: number | null
    username: string | null
  }
  timer: TimerSessionItem | null
  reminder: { enabled: boolean }
}

let cached: Promise<BootstrapData> | null = null

/** 取启动状态：进程内缓存，首个调用者发请求，其余共享同一次结果。 */
export function getBootstrap(force = false): Promise<BootstrapData> {
  if (!cached || force) {
    cached = request
      .get('/system/bootstrap')
      .then((r) => r.data.data as BootstrapData)
  }
  return cached
}

/** 清缓存（登出 / 令牌失效后调用，下次启动重新拉取）。 */
export function clearBootstrap() {
  cached = null
}

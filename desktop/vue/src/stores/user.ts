import { defineStore } from 'pinia'
import request from '@/api/request'
import { getBootstrap, clearBootstrap } from '@/api/bootstrap'

// 本地账号状态：首次需初始化（setup），之后用用户名+密码登录（login）。
// 登录成功后端返回会话令牌，存 localStorage，由 request.ts 注入 Authorization 头。
export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('sm_access_token') || '',
    username: localStorage.getItem('sm_username') || '',
    setupDone: false,
    ready: false, // 是否已向后端确认过初始化状态
    hydrated: false, // Phase 6-4：是否已完成启动水合（/system/bootstrap）
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    needsSetup: (s) => s.ready && !s.setupDone && !s.token,
  },
  actions: {
    /** 启动检查：询问后端是否已初始化账号、本地是否有有效令牌。 */
    async bootstrap() {
      try {
        const res = await request.get('/auth/status')
        this.setupDone = !!(res?.data?.data?.setup_done)
      } catch {
        this.setupDone = false
      }
      this.ready = true
    },
    /**
     * 启动水合（Phase 6-4）：一次 /system/bootstrap 恢复用户态。
     * - 本地有 token 且后端认证通过 → 恢复用户信息；
     * - 本地有 token 但已失效 → 静默清除（避免「进了主页又弹回登录」闪跳）；
     * - setup_done 同时刷新。
     */
    async hydrate() {
      try {
        const data = await getBootstrap()
        this.setupDone = data.user.setup_done
        this.ready = true
        if (data.user.authenticated) {
          this.username = data.user.username || this.username
        } else if (this.token) {
          // 令牌已失效：清除本地态，路由守卫会导向 /auth
          this.token = ''
          this.username = ''
          localStorage.removeItem('sm_access_token')
          localStorage.removeItem('sm_username')
          clearBootstrap()
        }
      } catch {
        this.setupDone = false
      } finally {
        this.hydrated = true
        this.ready = true
      }
    },
    async setup(username: string, password: string) {
      await request.post('/auth/setup', { username, password })
      this.setupDone = true
      await this.login(username, password)
    },
    async register(username: string, password: string) {
      const res = await request.post('/auth/register', { username, password })
      const token: string = res.data.data.token
      this.token = token
      this.username = username
      localStorage.setItem('sm_access_token', token)
      localStorage.setItem('sm_username', username)
    },
    async login(username: string, password: string) {
      const res = await request.post('/auth/login', { username, password })
      const token: string = res.data.data.token
      this.token = token
      this.username = username
      localStorage.setItem('sm_access_token', token)
      localStorage.setItem('sm_username', username)
    },
    logout() {
      try {
        request.post('/auth/logout')
      } catch {
        /* ignore */
      }
      this.token = ''
      this.username = ''
      localStorage.removeItem('sm_access_token')
      localStorage.removeItem('sm_username')
      clearBootstrap()
    },
  },
})

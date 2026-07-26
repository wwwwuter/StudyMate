import { defineStore } from 'pinia'
import request from '@/api/request'

interface Tokens {
  access_token: string
  refresh_token: string
  expires_in?: number
  token_type?: string
}
interface UserProfile {
  id: number
  nickname?: string
  avatar?: string
  [key: string]: unknown
}

// 用户与鉴权状态。
// 说明：本阶段尚未实现微信扫码登录 UI，桌面端采用「开发态静默登录」——
// 通过 WECHAT_MOCK 模式用 code 换取令牌，保证学习计划接口可端到端联通。
// 正式扫码登录 UI 留待用户系统前端阶段（Phase 2 前端）替换 ensureToken 逻辑。
export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('sm_access_token') || '',
    user: JSON.parse(localStorage.getItem('sm_user') || 'null') as UserProfile | null,
  }),
  actions: {
    /** 确保存在有效令牌；无则静默登录一次。幂等。 */
    async ensureToken() {
      if (this.token) return
      await this.login('desktop_dev')
    },
    async login(code: string) {
      const { data } = await request.post('/auth/wechat/login', { code })
      const token: Tokens = data.data.token
      this.token = token.access_token
      localStorage.setItem('sm_access_token', token.access_token)
      localStorage.setItem('sm_refresh_token', token.refresh_token)
      this.user = data.data.user as UserProfile
      localStorage.setItem('sm_user', JSON.stringify(this.user))
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('sm_access_token')
      localStorage.removeItem('sm_refresh_token')
      localStorage.removeItem('sm_user')
    },
  },
})

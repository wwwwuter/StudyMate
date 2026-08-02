import { createRouter, createWebHashHistory } from 'vue-router'
import MainLayout from '../layout/MainLayout.vue'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  // 用 hash 路由：Electron file:// 协议下 createWebHistory 无法正确匹配路径，
  // 导致 router-view 为空、界面白屏。hash 路由用 #/ 导航，不依赖服务器。
  history: createWebHashHistory(),
  routes: [
    { path: '/auth', name: 'auth', component: () => import('../views/AuthView.vue') },
    {
      path: '/',
      component: MainLayout,
      children: [
        { path: '', name: 'dashboard', component: () => import('../views/Dashboard.vue') },
        { path: 'upload', name: 'upload', component: () => import('../views/UploadPlanView.vue') },
        { path: 'tasks', name: 'tasks', component: () => import('../views/TasksView.vue') },
        { path: 'timer', name: 'timer', component: () => import('../views/TimerView.vue') },
        { path: 'stats', name: 'stats', component: () => import('../views/stat/StudyStat.vue') },
        { path: 'settings', name: 'settings', component: () => import('../views/SettingsView.vue') },
      ],
    },
  ],
})

// 本地账号门禁：未初始化或未登录一律进 /auth
router.beforeEach(async (to) => {
  const user = useUserStore()
  if (!user.ready) {
    await user.bootstrap()
  }
  if (to.path === '/auth') return true
  if (!user.setupDone) return { path: '/auth' }
  if (!user.isLoggedIn) return { path: '/auth' }
  return true
})

export default router

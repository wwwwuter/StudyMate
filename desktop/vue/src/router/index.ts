import { createRouter, createWebHashHistory } from 'vue-router'
import MainLayout from '../layout/MainLayout.vue'

const router = createRouter({
  // 用 hash 路由：Electron file:// 协议下 createWebHistory 无法正确匹配路径，
  // 导致 router-view 为空、界面白屏。hash 路由用 #/ 导航，不依赖服务器。
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      component: MainLayout,
      children: [
        { path: '', name: 'dashboard', component: () => import('../views/Dashboard.vue') },
        { path: 'plan', component: () => import('../views/TasksView.vue') },
        { path: 'tasks', component: () => import('../views/TasksView.vue') },
        { path: 'timer', component: () => import('../views/TimerView.vue') },
        { path: 'materials', component: () => import('../views/MaterialsView.vue') },
        { path: 'ai', component: () => import('../views/RagView.vue') },
        { path: 'stats', component: () => import('../views/AnalyticsView.vue') },
        { path: 'settings', component: () => import('../views/ComingSoon.vue') },
      ],
    },
  ],
})

export default router

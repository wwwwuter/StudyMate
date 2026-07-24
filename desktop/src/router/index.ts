import { createRouter, createWebHashHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/login',
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    redirect: '/home/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '学习看板' },
      },
      {
        path: 'tasks',
        name: 'Tasks',
        component: () => import('@/views/Tasks.vue'),
        meta: { title: '学习任务' },
      },
      {
        path: 'timer',
        name: 'Timer',
        component: () => import('@/views/Timer.vue'),
        meta: { title: '学习计时' },
      },
      {
        path: 'stats',
        name: 'Stats',
        component: () => import('@/views/Stats.vue'),
        meta: { title: '学习统计' },
      },
      {
        path: 'ai',
        name: 'AIAssistant',
        component: () => import('@/views/AIAssistant.vue'),
        meta: { title: 'AI 助手' },
      },
      {
        path: 'import',
        name: 'ImportPlan',
        component: () => import('@/views/ImportPlan.vue'),
        meta: { title: '导入计划' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

// 路由守卫：检查登录状态
router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('studymate_token')
  if (to.path !== '/login' && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
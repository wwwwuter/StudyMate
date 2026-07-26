import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layout/MainLayout.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: MainLayout,
      children: [
        { path: '', name: 'dashboard', component: () => import('../views/Dashboard.vue') },
        { path: 'plan', component: () => import('../views/TasksView.vue') },
        { path: 'tasks', component: () => import('../views/TasksView.vue') },
        { path: 'ai', component: () => import('../views/ComingSoon.vue') },
        { path: 'stats', component: () => import('../views/ComingSoon.vue') },
        { path: 'settings', component: () => import('../views/ComingSoon.vue') },
      ],
    },
  ],
})

export default router

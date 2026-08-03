import { createApp } from 'vue'
import { createPinia, setActivePinia } from 'pinia'

import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'

import './theme/index.css'


const app = createApp(App)

// 全局错误兜底：把未捕获的渲染/异步错误写到页面，避免直接白屏。
app.config.errorHandler = (err, instance, info) => {
  console.error('[Vue error]', err, info, instance)
  const msg = err instanceof Error ? err.message : String(err)
  showFatalOverlay(`页面渲染出错：${msg}`)
}
window.addEventListener('error', (e) => {
  console.error('[window error]', e.error)
  showFatalOverlay(`脚本错误：${e.error?.message || e.message}`)
})
window.addEventListener('unhandledrejection', (e) => {
  console.error('[unhandled rejection]', e.reason)
  const reason = e.reason instanceof Error ? e.reason.message : String(e.reason)
  showFatalOverlay(`未处理的异步错误：${reason}`)
})

function showFatalOverlay(text: string) {
  const el = document.getElementById('app')
  if (!el) return
  // 避免重复覆盖
  if (el.querySelector('.sm-fatal-overlay')) return
  const div = document.createElement('div')
  div.className = 'sm-fatal-overlay'
  div.style.cssText = 'position:fixed;inset:0;background:#fff;padding:40px;z-index:99999;font-family:sans-serif;color:#333;overflow:auto;'
  div.innerHTML = `<h2 style="color:#c00">StudyMate 出错了</h2><p style="white-space:pre-wrap">${text}</p><p style="margin-top:20px;color:#666">请截图并联系开发者，或重启应用。</p>`
  el.appendChild(div)
}

const pinia = createPinia()
setActivePinia(pinia)
app.use(pinia)
app.use(router)
app.use(ElementPlus)

/**
 * Phase 6-4：启动水合（先恢复状态，再挂载页面）。
 * user → timer → reminder 三个 store 共享同一次 /system/bootstrap 请求，
 * 在挂载前完成登录态校验与计时/提醒恢复，避免「登录页 → 主页 → 计时恢复」闪跳。
 */
async function bootstrap() {
  const { useUserStore } = await import('./stores/user')
  const { useTimerStore } = await import('./stores/timer')
  const { useReminderStore } = await import('./stores/reminder')
  const user = useUserStore()
  const timer = useTimerStore()
  const reminder = useReminderStore()
  await user.hydrate()
  await timer.hydrate()
  await reminder.hydrate()
}

bootstrap().finally(() => {
  app.mount('#app')
})
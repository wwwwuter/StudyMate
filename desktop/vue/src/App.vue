<template>
  <router-view />
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue'
import { ElNotification } from 'element-plus'
import { useScheduler } from '@/composables/useScheduler'
import { useAiKey } from '@/composables/useAiKey'

// 启动调度器：周期拉取待提醒并弹系统通知（桌面 OS 通知 / 浏览器 Notification），
// 计划到点自动开启计时。
useScheduler()

// 应用启动时预加载 AI Key 状态（供全局 ensureKey 检查）
const { load: loadAiKey } = useAiKey()

// 自动更新提示：仅 Electron 打包态有 electronAPI；Web 下 electronAPI 为 undefined，不触发。
let unsubscribe: (() => void) | null = null

function showUpdate(ui: any) {
  const api = (window as any).electronAPI
  if (!api?.onUpdateStatus) return
  switch (ui.state) {
    case 'checking':
      ElNotification({ title: '更新', message: '正在检查更新…', duration: 2000 })
      break
    case 'available':
      ElNotification({ title: '发现新版本', message: `新版本 ${ui.version || ''} 开始下载`, duration: 3000 })
      break
    case 'downloaded':
      ElNotification({ title: '更新就绪', message: '点击此通知重启并安装更新', duration: 0, onClick: () => api.restartAndInstall?.() })
      break
    case 'error':
      ElNotification({ title: '更新失败', message: ui.message || '请稍后重试', type: 'warning', duration: 4000 })
      break
  }
}

onMounted(() => {
  const api = (window as any).electronAPI
  if (api?.onUpdateStatus) {
    unsubscribe = api.onUpdateStatus(showUpdate)
  }
  loadAiKey()
})

onBeforeUnmount(() => {
  unsubscribe?.()
})
</script>

<style>
#app {
  width: 100%;
  height: 100vh;
}
</style>

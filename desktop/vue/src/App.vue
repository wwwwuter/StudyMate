<template>
  <router-view />
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue'
import { ElNotification } from 'element-plus'
import { useReminders } from '@/composables/useReminders'

// 启动提醒轮询：定时拉取未送达提醒并弹出系统通知（Electron 系统通知）
useReminders()

// 自动更新状态提示（仅 Electron 打包态有 electronAPI）
let unsubscribe: (() => void) | null = null

function showUpdate(ui: any) {
  const api = (window as any).electronAPI
  if (!api?.onUpdateStatus) return
  switch (ui.state) {
    case 'checking':
      ElNotification({ title: '更新', message: '正在检查更新…', duration: 2000 })
      break
    case 'available':
      ElNotification({
        title: '发现新版本',
        message: `新版本 ${ui.version || ''} 开始下载`,
        duration: 3000,
      })
      break
    case 'downloaded':
      ElNotification({
        title: '更新就绪',
        message: '点击此通知重启并安装更新',
        duration: 0,
        onClick: () => api.restartAndInstall?.(),
      })
      break
    case 'error':
      ElNotification({
        title: '更新失败',
        message: ui.message || '请稍后重试',
        type: 'warning',
        duration: 4000,
      })
      break
    // 'not-available' / 'downloading' 静默处理，避免打扰
  }
}

onMounted(() => {
  const api = (window as any).electronAPI
  if (api?.onUpdateStatus) {
    unsubscribe = api.onUpdateStatus(showUpdate)
  }
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

<template>
  <router-view />
</template>

<script setup lang="ts">
import { useUserStore } from '@/stores/user'
import { useTaskStore } from '@/stores/task'

const userStore = useUserStore()
const taskStore = useTaskStore()

// 初始化时尝试恢复登录状态
userStore.initAuth()
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-thumb {
  background: #c0c4cc;
  border-radius: 3px;
}

::-webkit-scrollbar-track {
  background: transparent;
}
</style>
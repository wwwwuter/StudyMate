<template>
  <router-view />
</template>

<script setup lang="ts">
import { useReminders } from '@/composables/useReminders'

// 启动提醒轮询：定时拉取未送达提醒并弹出系统通知（Electron 系统通知）
useReminders()
</script>

<style>
#app {
  width: 100%;
  height: 100vh;
}
</style>

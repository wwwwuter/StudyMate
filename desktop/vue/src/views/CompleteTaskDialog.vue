<template>
  <el-dialog
    v-model="visible"
    title="🎉 本次学习完成"
    width="400px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
    class="complete-dialog"
  >
    <div class="complete-body">
      <div class="c-row">
        <span class="c-label">任务</span>
        <span class="c-task">{{ taskName }}</span>
      </div>
      <div class="c-row">
        <span class="c-label">学习时间</span>
        <span class="c-time">{{ fmtDuration }}</span>
      </div>
      <p class="c-question">是否完成任务？</p>
      <p class="c-tip">选择「完成任务」将计入计划完成率；「继续学习」会立即重新开始计时。</p>
    </div>
    <template #footer>
      <el-button @click="decide('later')">稍后处理</el-button>
      <el-button type="primary" plain @click="decide('continue')">继续学习</el-button>
      <el-button type="success" @click="decide('done')">完成任务</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useTimerStore } from '@/stores/timer'

const timer = useTimerStore()
const { pendingComplete } = storeToRefs(timer)

const visible = computed({
  get: () => !!pendingComplete.value,
  set: (v: boolean) => {
    // 点遮罩/关闭被禁用，不会走到这里；兜底当作「稍后处理」
    if (!v) timer.decideTaskComplete('later')
  },
})

const taskName = computed(
  () => pendingComplete.value?.session.task?.content || pendingComplete.value?.session.task?.subject || '任务计时',
)

const fmtDuration = computed(() => {
  const sec = pendingComplete.value?.session.duration_seconds || 0
  const m = Math.floor(sec / 60)
  const h = Math.floor(m / 60)
  return h > 0 ? `${h} 小时 ${m % 60} 分钟` : `${m} 分钟`
})

function decide(action: 'done' | 'continue' | 'later') {
  timer.decideTaskComplete(action)
}
</script>

<style scoped>
.complete-body { padding: 4px 0 8px; }
.c-row { display: flex; gap: 12px; align-items: baseline; margin-bottom: 10px; font-size: 14px; }
.c-label { width: 64px; color: var(--text-muted, #6b7280); flex-shrink: 0; }
.c-task { font-weight: 600; color: var(--text-strong, #111827); word-break: break-all; }
.c-time { font-weight: 600; color: var(--brand-700, #0F766E); }
.c-question { margin: 14px 0 4px; font-size: 14px; font-weight: 600; color: var(--text-strong, #111827); }
.c-tip { margin: 0; font-size: 12px; color: var(--text-muted, #9ca3af); line-height: 1.6; }
</style>

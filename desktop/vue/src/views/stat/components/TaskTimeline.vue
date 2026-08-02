<template>
  <div class="timeline-card">
    <div class="block-title">今日任务时间轴</div>

    <div v-if="!tasks.length" class="empty">今天还没有安排学习任务，去「上传计划」排期吧。</div>

    <ul v-else class="task-list">
      <li
        v-for="t in tasks"
        :key="t.id"
        class="task-item"
        @click="$emit('open', t)"
      >
        <div class="task-time">{{ t.start_time || '—' }}</div>
        <div class="task-dot" :class="`dot-${t.status}`" />
        <div class="task-body">
          <div class="task-subject">{{ t.subject }}</div>
          <div class="task-content">{{ t.content }}</div>
        </div>
        <el-tag size="small" :type="statusType(t.status)" effect="light" class="task-tag">
          {{ statusText(t.status) }}
        </el-tag>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import type { TodayTaskItem } from '@/api/stat'

defineProps<{ tasks: TodayTaskItem[] }>()
defineEmits<{ (e: 'open', task: TodayTaskItem): void }>()

function statusType(s: TodayTaskItem['status']): 'info' | 'primary' | 'success' | 'warning' {
  if (s === 'done') return 'success'
  if (s === 'doing') return 'primary'
  if (s === 'overdue') return 'warning'
  return 'info'
}
function statusText(s: TodayTaskItem['status']): string {
  return { pending: '未开始', doing: '进行中', done: '已完成', overdue: '超时' }[s]
}
</script>

<style scoped>
.timeline-card {
  background: #fff;
  border: 1px solid #eef1f4;
  border-radius: 14px;
  padding: 16px 18px;
  box-shadow: 0 2px 10px rgba(15, 118, 110, 0.05);
}
.block-title {
  font-size: 15px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 12px;
}
.empty {
  font-size: 13px;
  color: #aab2bf;
  padding: 18px 4px;
  text-align: center;
}
.task-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.task-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 6px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s ease;
}
.task-item:hover {
  background: #f6fbfa;
}
.task-time {
  width: 48px;
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 600;
  color: #6b7280;
  font-variant-numeric: tabular-nums;
}
.task-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot-pending { background: #cbd5e1; }
.dot-doing { background: #0f766e; }
.dot-done { background: #22c55e; }
.dot-overdue { background: #f59e0b; }
.task-body {
  flex: 1;
  min-width: 0;
}
.task-subject {
  font-size: 14px;
  font-weight: 700;
  color: #1f2937;
}
.task-content {
  font-size: 12px;
  color: #8a94a6;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.task-tag {
  flex-shrink: 0;
}
</style>

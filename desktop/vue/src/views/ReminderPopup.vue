<template>
  <el-dialog
    v-model="visible"
    width="420px"
    align-center
    :show-close="true"
    class="reminder-pop"
    @close="onClose"
  >
    <template #header>
      <div class="rp-head">
        <el-icon :size="20" color="#0F766E"><BellFilled /></el-icon>
        <span>学习提醒</span>
      </div>
    </template>

    <div v-if="current" class="rp-body">
      <div class="rp-subject">
        <el-tag :class="subjectClass(current.subject)" effect="light" round>{{ current.subject }}</el-tag>
        <span class="rp-round">{{ roundLabel }}</span>
      </div>
      <div class="rp-content">{{ current.content }}</div>
      <div class="rp-meta">计划于 {{ current.fire_at }}<template v-if="isToday">（今天）</template></div>
    </div>

    <template #footer>
      <div class="rp-actions">
        <el-button text @click="dismissAll">稍后提醒</el-button>
        <el-button v-if="current?.task_id" @click="goTimer">开始计时</el-button>
        <el-button type="primary" @click="ackCurrent">知道了</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { BellFilled } from '@element-plus/icons-vue'
import { getPendingReminders, ackReminders, type ReminderItem } from '@/api/reminder'

const router = useRouter()
const POLL_MS = 15_000
const visible = ref(false)
const queue = ref<ReminderItem[]>([])
const ackedIds = ref<Set<number>>(new Set())
let timer: number | undefined

const current = computed(() => queue.value[0] || null)
const isToday = computed(() => {
  if (!current.value) return false
  return current.value.fire_at?.startsWith(new Date().toISOString().slice(0, 10))
})
const roundLabel = computed(() => {
  const c = current.value
  if (!c) return ''
  // 尝试从内容识别复习轮次（【复习】前缀）
  if (c.content.startsWith('【复习】')) return '复习任务'
  return '首次学习'
})

const subjectColor: Record<string, string> = {
  数学: 'subj-数学', 英语: 'subj-英语', 政治: 'subj-政治', 408: 'subj-408',
}
function subjectClass(subject?: string): string {
  return subjectColor[subject || ''] || 'subj-other'
}

async function poll() {
  try {
    const res = await getPendingReminders()
    const incoming = (res.data || []).filter((r) => !ackedIds.value.has(r.id))
    if (incoming.length) {
      // 合并去重，保留未展示的
      const have = new Set(queue.value.map((q) => q.id))
      for (const r of incoming) if (!have.has(r.id)) queue.value.push(r)
      if (!visible.value) visible.value = true
    }
  } catch {
    /* 忽略瞬时错误，下次轮询重试 */
  }
}

async function ackCurrent() {
  const c = current.value
  if (!c) return
  ackedIds.value.add(c.id)
  queue.value = queue.value.slice(1)
  try {
    await ackReminders([c.id])
  } catch {
    /* 忽略 */
  }
  if (!queue.value.length) visible.value = false
}

async function dismissAll() {
  const ids = queue.value.map((q) => q.id)
  ackedIds.value = new Set([...ackedIds.value, ...ids])
  try {
    if (ids.length) await ackReminders(ids)
  } catch {
    /* 忽略 */
  }
  queue.value = []
  visible.value = false
}

function onClose() {
  // 用户点了右上角关闭：等同当前条目稍后（不 ack，下次仍会弹）
  queue.value = queue.value.slice(1)
  if (!queue.value.length) visible.value = false
}

function goTimer() {
  const id = current.value?.task_id
  ackCurrent()
  if (id) router.push({ path: '/timer', query: { taskId: String(id) } })
}

onMounted(() => {
  poll()
  timer = window.setInterval(poll, POLL_MS)
})
onBeforeUnmount(() => {
  if (timer !== undefined) clearInterval(timer)
})
</script>

<style scoped>
.reminder-pop :deep(.el-dialog__header) { padding-bottom: 8px; }
.rp-head { display: flex; align-items: center; gap: 8px; font-weight: 700; color: var(--text-strong); }
.rp-body { padding: 4px 2px; }
.rp-subject { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.rp-round { font-size: 12px; color: var(--text-muted); }
.rp-content { font-size: 16px; font-weight: 600; color: var(--text-strong); line-height: 1.5; }
.rp-meta { margin-top: 8px; font-size: 12px; color: var(--text-muted); }
.rp-actions { display: flex; justify-content: flex-end; gap: 8px; }

.subj-数学 { background: #0F766E1A; color: #0F766E; border-color: #0F766E55; }
.subj-英语 { background: #0EA5E91A; color: #0EA5E9; border-color: #0EA5E955; }
.subj-政治 { background: #F59E0B1A; color: #B45309; border-color: #F59E0B55; }
.subj-408 { background: #8B5CF61A; color: #7C3AED; border-color: #8B5CF655; }
.subj-other { background: #64748B1A; color: #475569; border-color: #64748B55; }
</style>

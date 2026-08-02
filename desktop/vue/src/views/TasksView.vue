<template>
  <div class="tasks-view">
    <div class="head">
      <div class="head-left">
        <el-button text circle @click="shiftDay(-1)" title="前一天">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <div class="head-title">
          <h3>{{ dayLabel }}</h3>
          <span v-if="daySummary" class="head-sub">{{ daySummary }}</span>
        </div>
        <el-button text circle @click="shiftDay(1)" title="后一天">
          <el-icon><ArrowRight /></el-icon>
        </el-button>
        <el-button v-if="selectedDate !== todayStr()" size="small" @click="goToday">回到今天</el-button>
      </div>
      <el-button text type="primary" @click="showAdd = !showAdd">
        <el-icon><Plus /></el-icon> 快速添加
      </el-button>
    </div>

    <!-- 快速添加 -->
    <el-card v-if="showAdd" shadow="never" class="add-card">
      <el-form :inline="true" class="add-form">
        <el-form-item label="科目">
          <el-input v-model="add.subject" placeholder="如 数学" style="width: 120px" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="add.content" placeholder="如 高数第三章" style="width: 200px" />
        </el-form-item>
        <el-form-item label="开始">
          <el-time-picker v-model="add.start_time" format="HH:mm" value-format="HH:mm" placeholder="开始" style="width: 120px" />
        </el-form-item>
        <el-form-item label="结束">
          <el-time-picker v-model="add.end_time" format="HH:mm" value-format="HH:mm" placeholder="结束" style="width: 120px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="adding" @click="addPlan">添加</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 时间轴 -->
    <div v-if="!tasks.length" class="empty">这天还没有计划，去「上传计划」让 AI 帮你排期，或点上方「快速添加」。</div>
    <ul v-else class="timeline">
      <li v-for="t in tasks" :key="t.id" class="tl-item" :class="rowClass(t)">
        <div class="tl-time">
          <div class="tl-start">{{ t.start_time || '—' }}</div>
          <div v-if="t.end_time" class="tl-end">{{ t.end_time }}</div>
        </div>
        <div class="tl-rail"><span class="tl-dot" /></div>
        <div class="tl-body">
          <div class="tl-top">
            <span class="tl-subj">{{ t.subject }}</span>
            <el-tag size="small" :type="tagType(t)">{{ tagText(t) }}</el-tag>
            <span v-if="countdown(t)" class="tl-count">{{ countdown(t) }}</span>
          </div>
          <div class="tl-content">{{ t.content }}</div>
          <div class="tl-actions" v-if="t.status === 'pending'">
            <el-button size="small" type="primary" @click="startTask(t)">开始计时</el-button>
            <el-button size="small" @click="markDone(t)">完成</el-button>
            <el-button size="small" text type="danger" @click="cancelTask(t)">取消</el-button>
          </div>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { listTasks, createTask, updateTask, dailyStats, type TaskItem } from '@/api/task'
import { startTimer, getTimerCurrent, type TimerSessionItem } from '@/api/plan'

const router = useRouter()
const tasks = ref<TaskItem[]>([])
const current = ref<TimerSessionItem | null>(null)
const showAdd = ref(false)
const adding = ref(false)
const add = ref({ subject: '', content: '', start_time: '', end_time: '' })
const now = ref(Date.now())
let tick: number | undefined

const todayStr = () => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const selectedDate = ref(todayStr())

function fmtDate(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
function shiftDay(delta: number) {
  const d = new Date(selectedDate.value)
  d.setDate(d.getDate() + delta)
  selectedDate.value = fmtDate(d)
  load()
}
function goToday() {
  selectedDate.value = todayStr()
  load()
}

const dayLabel = computed(() => {
  if (selectedDate.value === todayStr()) return '今日计划'
  const d = new Date(selectedDate.value)
  const wd = ['日', '一', '二', '三', '四', '五', '六'][d.getDay()]
  return `${selectedDate.value} 周${wd}`
})
const daySummary = ref('')

function toSec(hhmm: string) {
  const [h, m] = hhmm.split(':').map(Number)
  return (h || 0) * 3600 + (m || 0) * 60
}

async function load() {
  try {
    const [t, c, s] = await Promise.all([
      listTasks({ date: selectedDate.value }),
      getTimerCurrent(),
      dailyStats(selectedDate.value),
    ])
    const list = t.data || []
    tasks.value = list.slice().sort((a, b) => (a.start_time || '99:99').localeCompare(b.start_time || '99:99'))
    current.value = c.data || null
    const st = s
    daySummary.value =
      st && st.total ? `共 ${st.total} 项 · 已完成 ${st.done} · 完成率 ${st.completion_rate}%` : '当天暂无计划'
  } catch {
    /* ignore */
  }
}

const isRunning = (t: TaskItem) => current.value?.task_id === t.id

function rowClass(t: TaskItem) {
  return {
    done: t.status === 'done',
    cancelled: t.status === 'cancelled',
    running: isRunning(t),
  }
}
function tagType(t: TaskItem): 'success' | 'info' | 'warning' | 'primary' {
  if (isRunning(t)) return 'primary'
  if (t.status === 'done') return 'success'
  if (t.status === 'cancelled') return 'info'
  return 'warning'
}
function tagText(t: TaskItem) {
  if (isRunning(t)) return '进行中'
  if (t.status === 'done') return '已完成'
  if (t.status === 'cancelled') return '已取消'
  return '待开始'
}
function countdown(t: TaskItem) {
  if (selectedDate.value !== todayStr()) return ''
  if (t.status !== 'pending' || !t.start_time) return ''
  const diff = toSec(t.start_time) - toSec(new Date(now.value).toTimeString().slice(0, 5))
  if (diff > 0) {
    const m = Math.floor(diff / 60)
    return m >= 60 ? `还有 ${Math.floor(m / 60)} 小时 ${m % 60} 分` : `还有 ${m} 分钟开始`
  }
  return '已开始，待计时'
}

async function startTask(t: TaskItem) {
  try {
    await startTimer({ task_id: t.id })
    router.push('/timer')
  } catch (e: any) {
    ElMessage.error(e?.message || '开始计时失败')
  }
}
async function markDone(t: TaskItem) {
  try {
    await updateTask(t.id, { status: 'done' })
    await load()
  } catch {
    /* ignore */
  }
}
async function cancelTask(t: TaskItem) {
  try {
    await updateTask(t.id, { status: 'cancelled' })
    await load()
  } catch {
    /* ignore */
  }
}
async function addPlan() {
  if (!add.value.subject.trim() || !add.value.content.trim()) {
    ElMessage.warning('科目和内容不能为空')
    return
  }
  adding.value = true
  try {
    await createTask({
      date: selectedDate.value,
      subject: add.value.subject.trim(),
      content: add.value.content.trim(),
      start_time: add.value.start_time || null,
      end_time: add.value.end_time || null,
      status: 'pending',
      plan_source: 'manual',
    })
    ElMessage.success('已添加计划')
    add.value = { subject: '', content: '', start_time: '', end_time: '' }
    showAdd.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(e?.message || '添加失败')
  } finally {
    adding.value = false
  }
}

onMounted(async () => {
  await load()
  tick = window.setInterval(() => { now.value = Date.now() }, 1000)
})
onBeforeUnmount(() => { if (tick) clearInterval(tick) })
</script>

<style scoped>
.tasks-view { max-width: 900px; margin: 0 auto; }
.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.head-left { display: flex; align-items: center; gap: 10px; }
.head-title h3 { margin: 0; font-size: 18px; line-height: 1.2; }
.head-sub { display: block; font-size: 12px; color: var(--text-muted); margin-top: 2px; }
.head h3 { margin: 0; font-size: 18px; }
.add-card { border-radius: 14px; margin-bottom: 16px; }
.add-form { display: flex; flex-wrap: wrap; align-items: flex-end; gap: 4px; }
.empty { color: var(--text-muted); font-size: 13px; padding: 40px 0; text-align: center; }

.timeline { list-style: none; margin: 0; padding: 0; }
.tl-item { display: flex; gap: 14px; padding-bottom: 18px; }
.tl-time { width: 64px; text-align: right; padding-top: 2px; }
.tl-start { font-weight: 700; font-variant-numeric: tabular-nums; color: var(--text-strong); }
.tl-end { font-size: 12px; color: var(--text-muted); }
.tl-rail { position: relative; width: 14px; display: flex; justify-content: center; }
.tl-rail::before { content: ''; position: absolute; top: 6px; bottom: -18px; width: 2px; background: var(--border); }
.tl-item:last-child .tl-rail::before { display: none; }
.tl-dot { width: 12px; height: 12px; border-radius: 50%; background: var(--brand-700, #0F766E); margin-top: 4px; z-index: 1; }
.tl-item.done .tl-dot { background: var(--el-color-success); }
.tl-item.cancelled .tl-dot { background: var(--el-color-info); }
.tl-item.running .tl-dot { box-shadow: 0 0 0 4px rgba(15,118,110,.18); }
.tl-body { flex: 1; background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 12px 14px; }
.tl-item.running .tl-body { border-color: var(--brand-700, #0F766E); }
.tl-top { display: flex; align-items: center; gap: 10px; }
.tl-subj { font-weight: 700; color: var(--text-strong); }
.tl-count { margin-left: auto; font-size: 12px; color: var(--brand-700, #0F766E); }
.tl-content { color: var(--text-secondary); margin: 6px 0 10px; }
.tl-item.done .tl-content, .tl-item.cancelled .tl-content { text-decoration: line-through; opacity: .6; }
.tl-actions { display: flex; gap: 8px; }
</style>

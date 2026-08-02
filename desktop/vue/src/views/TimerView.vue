<template>
  <div class="timer-page">
    <!-- 进行中 -->
    <el-card v-if="current" shadow="never" class="run-card">
      <div class="run-label">
        <el-tag v-if="mode === 'pomodoro' && pomodoroActive" :type="pomoPhase === 'work' ? 'danger' : 'success'" size="small">
          {{ pomoPhase === 'work' ? '🍅 专注中' : '☕ 休息中' }}
        </el-tag>
        <el-tag v-else-if="current.task" type="primary" size="small">{{ current.task.subject }}</el-tag>
        <el-tag v-else type="info" size="small">自由计时</el-tag>
        <span v-if="current.note" class="run-note">· {{ current.note }}</span>
      </div>
      <div class="run-clock">{{ clockText }}</div>
      <div class="run-sub">
        <template v-if="mode === 'pomodoro' && pomodoroActive">
          {{ pomoPhase === 'work' ? '专注剩余' : '休息剩余' }}
        </template>
        <template v-else-if="current.task">
          {{ current.task.content }}
        </template>
        <template v-else>已计时</template>
      </div>
      <div class="run-actions">
        <el-button type="warning" size="large" @click="stop">结束并保存</el-button>
      </div>
    </el-card>

    <!-- 未开始：选择模式 -->
    <el-card v-else shadow="never" class="start-card">
      <el-tabs v-model="mode" class="modes">
        <!-- 计划计时 -->
        <el-tab-pane label="计划计时" name="task">
          <p class="mode-hint">选择今日一个计划，到点自动或手动开始计时。</p>
          <div v-if="!planTasks.length" class="empty">今日暂无待开始计划，可切换「自由计时」。</div>
          <ul v-else class="pick-list">
            <li v-for="t in planTasks" :key="t.id" class="pick-item">
              <span class="pk-time">{{ t.start_time || '—' }}</span>
              <span class="pk-subj">{{ t.subject }}</span>
              <span class="pk-content">{{ t.content }}</span>
              <el-button size="small" type="primary" @click="startTask(t)">开始</el-button>
            </li>
          </ul>
        </el-tab-pane>

        <!-- 番茄钟 -->
        <el-tab-pane label="番茄钟" name="pomodoro">
          <div class="pomo-config">
            <span>专注 <el-input-number v-model="workMin" :min="1" :max="90" size="small" /> 分</span>
            <span>休息 <el-input-number v-model="breakMin" :min="1" :max="30" size="small" /> 分</span>
          </div>
          <p class="mode-hint">开始后生成为期一个番茄周期的自由计时，结束自动保存。</p>
          <el-button type="primary" size="large" @click="startPomodoro">开始番茄钟</el-button>
        </el-tab-pane>

        <!-- 自由计时 -->
        <el-tab-pane label="自由计时" name="free">
          <el-input v-model="freeNote" placeholder="可选备注，如「背单词 30 分钟」" class="free-note" />
          <p class="mode-hint">不绑定计划，手动开始 / 结束。</p>
          <el-button type="primary" size="large" @click="startFree">开始自由计时</el-button>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { startTimer, stopTimer, getTimerCurrent, reportPomodoroCycle, type TimerSessionItem } from '@/api/plan'
import { listTasks, type TaskItem } from '@/api/task'

const route = useRoute()
type Mode = 'task' | 'pomodoro' | 'free'
const mode = ref<Mode>('task')
const current = ref<TimerSessionItem | null>(null)
const planTasks = ref<TaskItem[]>([])
const freeNote = ref('')
const now = ref(Date.now())

// 番茄钟本地状态
const workMin = ref(25)
const breakMin = ref(5)
const pomodoroActive = ref(false)
const pomoPhase = ref<'work' | 'break'>('work')
const pomoLeft = ref(0)
const pomoCycle = ref(1)

let timer: number | undefined

function fmt(s: number): string {
  s = Math.max(0, Math.floor(s))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  const mm = String(m).padStart(2, '0')
  const ss = String(sec).padStart(2, '0')
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`
}

const elapsedSec = computed(() => {
  if (!current.value || !current.value.started_at) return 0
  // 后端返回 UTC ISO-8601（如 2026-08-02T12:40:01Z），直接交给 Date 解析；
  // 若解析失败（NaN）则兜底为 0，避免界面出现 NaN:NaN。
  const startedAt = new Date(current.value.started_at).getTime()
  if (Number.isNaN(startedAt)) return 0
  return Math.floor((now.value - startedAt) / 1000)
})

const clockText = computed(() => {
  if (mode.value === 'pomodoro' && pomodoroActive.value) return fmt(pomoLeft.value)
  if (current.value) return fmt(elapsedSec.value)
  return '00:00'
})

const todayStr = () => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

async function loadTasks() {
  try {
    const res = await listTasks({ date: todayStr(), status: 'pending' })
    planTasks.value = res.data || []
  } catch {
    planTasks.value = []
  }
}

async function refresh() {
  try {
    const c = await getTimerCurrent()
    current.value = c.data || null
  } catch {
    current.value = null
  }
  await loadTasks()
}

async function startTask(t: TaskItem) {
  try {
    const res = await startTimer({ mode: 'task', task_id: t.id })
    current.value = res.data
    mode.value = 'task'
    pomodoroActive.value = false
  } catch (e: any) {
    ElMessage.error(e?.message || '开始计时失败')
  }
}

async function startPomodoro() {
  try {
    const res = await startTimer({ mode: 'pomodoro', duration: workMin.value * 60 })
    current.value = res.data
    mode.value = 'pomodoro'
    pomodoroActive.value = true
    pomoPhase.value = 'work'
    pomoLeft.value = workMin.value * 60
    pomoCycle.value = 1
  } catch (e: any) {
    ElMessage.error(e?.message || '开始失败')
  }
}

async function startFree() {
  try {
    const res = await startTimer({ mode: 'countup', note: freeNote.value.trim() || undefined })
    current.value = res.data
    mode.value = 'free'
    pomodoroActive.value = false
  } catch (e: any) {
    ElMessage.error(e?.message || '开始失败')
  }
}

/** 专注段结束上报一轮（番茄钟：只统计专注时长，休息不计入学习时长）。 */
async function reportCycle() {
  if (!current.value) return
  try {
    await reportPomodoroCycle({
      session_id: current.value.id,
      cycle_number: pomoCycle.value,
      focus_duration: workMin.value * 60,
      break_duration: breakMin.value * 60,
    })
    pomoCycle.value += 1
  } catch {
    // 上报失败不阻断番茄钟流程；最终统计会回退到整段时长
  }
}

async function stop(silent = false) {
  try {
    await stopTimer({})
  } catch (e: any) {
    if (!silent) ElMessage.error(e?.message || '结束失败')
  }
  current.value = null
  pomodoroActive.value = false
  mode.value = 'task'
  await loadTasks()
}

function tick() {
  now.value = Date.now()
  if (pomodoroActive.value && current.value) {
    pomoLeft.value--
    if (pomoLeft.value <= 0) {
      if (pomoPhase.value === 'work') {
        // 专注结束：先上报本轮（聚焦时长），再进入休息
        reportCycle().finally(() => {
          pomoPhase.value = 'break'
          pomoLeft.value = breakMin.value * 60
        })
      } else {
        // 休息结束：完成一个番茄周期，自动保存
        stop(true)
      }
    }
  }
}

onMounted(async () => {
  await refresh()
  // 从「今日计划」带 taskId 进入且当前无计时：直接开始
  const qTask = route.query.taskId
  if (qTask && !current.value) {
    const id = Number(qTask)
    const t = planTasks.value.find((x) => x.id === id)
    if (t) await startTask(t)
  }
  timer = window.setInterval(tick, 1000)
})
onBeforeUnmount(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.timer-page { max-width: 720px; margin: 0 auto; }
.run-card, .start-card { border-radius: 16px; text-align: center; padding: 28px 20px; }
.run-label { display: flex; align-items: center; justify-content: center; gap: 8px; }
.run-note { font-size: 13px; color: var(--text-muted); }
.run-clock { font-size: 68px; font-weight: 800; font-variant-numeric: tabular-nums; color: var(--brand-700, #0F766E); letter-spacing: 2px; margin: 14px 0 6px; }
.run-sub { color: var(--text-muted); font-size: 14px; margin-bottom: 20px; }
.run-actions { display: flex; justify-content: center; }

.modes { text-align: left; }
.mode-hint { font-size: 13px; color: var(--text-muted); margin: 8px 0 16px; }
.empty { color: var(--text-muted); font-size: 13px; padding: 16px 0; }
.pomo-config { display: flex; gap: 20px; justify-content: center; margin: 12px 0; font-size: 14px; }
.free-note { max-width: 360px; margin: 12px auto; }

.pick-list { list-style: none; margin: 0; padding: 0; }
.pick-item { display: flex; align-items: center; gap: 12px; padding: 10px 4px; border-bottom: 1px solid var(--border); }
.pick-item:last-child { border-bottom: none; }
.pk-time { width: 60px; font-weight: 600; color: var(--text-secondary); }
.pk-subj { width: 90px; font-weight: 600; color: var(--text-strong); }
.pk-content { flex: 1; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>

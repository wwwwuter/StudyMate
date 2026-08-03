<template>
  <div class="timer-page">
    <!-- 进行中 -->
    <el-card v-if="current" shadow="never" class="run-card">
      <div class="run-label">
        <el-tag v-if="mode === 'pomodoro'" :type="pomoPhase === 'work' ? 'danger' : 'success'" size="small">
          {{ pomoPhase === 'work' ? '🍅 专注中' : '☕ 休息中' }}
        </el-tag>
        <el-tag v-else-if="mode === 'countdown'" type="warning" size="small">⏳ 倒计时</el-tag>
        <el-tag v-else-if="current.task" type="primary" size="small">{{ current.task.subject }}</el-tag>
        <el-tag v-else type="info" size="small">自由计时</el-tag>
        <span v-if="current.note" class="run-note">· {{ current.note }}</span>
      </div>
      <div class="run-clock">{{ clockText }}</div>
      <div class="run-sub">
        <template v-if="mode === 'pomodoro'">
          {{ pomoPhase === 'work' ? '专注剩余' : '休息剩余' }}
        </template>
        <template v-else-if="mode === 'countdown'">
          倒计时剩余
        </template>
        <template v-else-if="current.task">
          {{ runSubText }}
        </template>
        <template v-else>已计时</template>
      </div>
      <div class="run-actions">
        <el-button type="warning" size="large" @click="timer.stop()">结束并保存</el-button>
      </div>
    </el-card>

    <!-- 未开始：选择模式 -->
    <el-card v-else shadow="never" class="start-card">
      <el-tabs v-model="tabMode" class="modes">
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

        <!-- 倒计时 -->
        <el-tab-pane label="倒计时" name="countdown">
          <div class="pomo-config">
            <span>目标 <el-input-number v-model="countdownMin" :min="1" :max="180" size="small" /> 分</span>
            <el-select
              v-model="countdownTaskId"
              placeholder="可选：绑定一个今日任务"
              clearable
              style="min-width: 200px"
              size="small"
            >
              <el-option
                v-for="t in planTasks"
                :key="t.id"
                :label="`${t.start_time || '—'} · ${t.subject} · ${t.content}`"
                :value="t.id"
              />
            </el-select>
          </div>
          <p class="mode-hint">到 0 自动结束并保存。可绑定任务以计入该任务的学习时间。</p>
          <el-button type="primary" size="large" @click="startCountdown">开始倒计时</el-button>
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
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useTimerStore } from '@/stores/timer'
import { listTasks, type TaskItem } from '@/api/task'

const route = useRoute()
const timer = useTimerStore()
const { session: current, mode, pomoPhase, clockText, runSubText } = storeToRefs(timer)

const planTasks = ref<TaskItem[]>([])
const freeNote = ref('')
// 未运行时选择的模式 Tab（本地 UI 状态，与 store.mode 无关）
const tabMode = ref<'task' | 'pomodoro' | 'countdown' | 'free'>('task')

// 番茄钟参数（本地配置）
const workMin = ref(25)
const breakMin = ref(5)

// 倒计时参数（本地配置）
const countdownMin = ref(25)
const countdownTaskId = ref<number | null>(null)

let tickTimer: number | undefined

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

async function startTask(t: TaskItem) {
  try { await timer.startTask(t) } catch { /* store 已提示 */ }
}

async function startPomodoro() {
  try { await timer.startPomodoro(workMin.value, breakMin.value) } catch { /* store 已提示 */ }
}

async function startCountdown() {
  const minutes = Math.max(1, Math.floor(countdownMin.value || 1))
  try { await timer.startCountdown(minutes, countdownTaskId.value) } catch { /* store 已提示 */ }
}

async function startFree() {
  try { await timer.startFree(freeNote.value.trim() || undefined) } catch { /* store 已提示 */ }
}

onMounted(async () => {
  await loadTasks()
  // 从「今日计划」带 taskId 进入且当前无计时：直接开始
  const qTask = route.query.taskId
  if (qTask && !current.value) {
    const id = Number(qTask)
    const t = planTasks.value.find((x) => x.id === id)
    if (t) await timer.startTask(t)
  }
  // 全局 tick：推进 store 时钟（番茄/倒计时归零、计划超时提示均在此处理）
  tickTimer = window.setInterval(() => timer.tick(), 1000)
})
onBeforeUnmount(() => { if (tickTimer) clearInterval(tickTimer) })
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
.pomo-config { display: flex; gap: 20px; justify-content: center; margin: 12px 0; font-size: 14px; align-items: center; flex-wrap: wrap; }
.free-note { max-width: 360px; margin: 12px auto; }

.pick-list { list-style: none; margin: 0; padding: 0; }
.pick-item { display: flex; align-items: center; gap: 12px; padding: 10px 4px; border-bottom: 1px solid var(--border); }
.pick-item:last-child { border-bottom: none; }
.pk-time { width: 60px; font-weight: 600; color: var(--text-secondary); }
.pk-subj { width: 90px; font-weight: 600; color: var(--text-strong); }
.pk-content { flex: 1; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
<template>
  <div class="timer-page">
    <el-row :gutter="20">
      <!-- 计时器 -->
      <el-col :xs="24" :lg="14">
        <el-card class="timer-card" shadow="never">
          <div class="mode-switch">
            <el-radio-group v-model="mode" :disabled="running" @change="resetTimer">
              <el-radio-button label="pomodoro">🍅 番茄钟</el-radio-button>
              <el-radio-button label="countup">⏱ 正计时</el-radio-button>
              <el-radio-button label="countdown">⏳ 倒计时</el-radio-button>
            </el-radio-group>
          </div>

          <div class="clock" :class="{ rest: mode === 'pomodoro' && phase === 'break' }">
            <div class="clock-time">{{ timeText }}</div>
            <div v-if="mode === 'pomodoro'" class="clock-phase">
              {{ phase === 'work' ? '专注中' : '休息中' }} · 已完成 {{ cycles }} 个番茄
            </div>
            <div v-else-if="mode === 'countdown'" class="clock-phase">目标 {{ targetMin }} 分钟</div>
            <div v-else class="clock-phase">累计专注</div>
          </div>

          <div class="config">
            <template v-if="mode === 'pomodoro'">
              <span>专注 <el-input-number v-model="workMin" :min="1" :max="90" :disabled="running" size="small" /> 分</span>
              <span>休息 <el-input-number v-model="breakMin" :min="1" :max="30" :disabled="running" size="small" /> 分</span>
            </template>
            <template v-else-if="mode === 'countdown'">
              <span>时长 <el-input-number v-model="targetMin" :min="1" :max="180" :disabled="running" size="small" /> 分</span>
            </template>
            <span>
              关联
              <el-select v-model="taskId" placeholder="可选任务" clearable size="small" style="width: 200px">
                <el-option v-for="t in tasks" :key="t.id" :label="`${t.date} ${t.subject} · ${t.content}`" :value="t.id" />
              </el-select>
            </span>
            <span v-if="taskId">
              科目
              <el-input v-model="subject" size="small" style="width: 120px" placeholder="自动带出" />
            </span>
          </div>

          <div class="controls">
            <el-button v-if="!running" type="primary" size="large" @click="start">开始</el-button>
            <el-button v-else type="warning" size="large" @click="pause">暂停</el-button>
            <el-button size="large" :disabled="!running && elapsed === 0 && !currentRecordId" @click="stop">停止并保存</el-button>
            <el-button size="large" text @click="resetTimer">重置</el-button>
          </div>
          <div v-if="saveTip" class="save-tip">{{ saveTip }}</div>
        </el-card>
      </el-col>

      <!-- 统计 -->
      <el-col :xs="24" :lg="10">
        <el-card class="stats-card" shadow="never">
          <div class="stats-head">
            <span>计时统计</span>
            <el-radio-group v-model="statsRange" size="small" @change="loadStats">
              <el-radio-button label="day">今天</el-radio-button>
              <el-radio-button label="week">本周</el-radio-button>
              <el-radio-button label="month">本月</el-radio-button>
              <el-radio-button label="all">全部</el-radio-button>
            </el-radio-group>
          </div>
          <div class="stat-big">
            <div class="stat-hours">{{ stats.total_hours }}<small>h</small></div>
            <div class="stat-sub">共 {{ stats.session_count }} 次 · {{ formatDur(stats.total_seconds) }}</div>
          </div>
          <el-row :gutter="12">
            <el-col :span="12"><div ref="pieRef" class="chart"></div></el-col>
            <el-col :span="12"><div ref="barRef" class="chart"></div></el-col>
          </el-row>
          <div ref="lineRef" class="chart chart-line"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 历史 -->
    <el-card class="history-card" shadow="never" style="margin-top: 20px">
      <div class="stats-head"><span>计时记录</span><el-button text size="small" @click="loadHistory">刷新</el-button></div>
      <el-table :data="history" stripe size="small">
        <el-table-column prop="mode" label="模式" width="110">
          <template #default="{ row }">
            <el-tag :type="row.mode === 'pomodoro' ? 'danger' : row.mode === 'countdown' ? 'warning' : 'success'" size="small">
              {{ modeLabel(row.mode) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="subject" label="科目" width="100" />
        <el-table-column label="开始" width="170">
          <template #default="{ row }">{{ row.start_time }}</template>
        </el-table-column>
        <el-table-column label="时长" width="100">
          <template #default="{ row }">{{ formatDur(row.duration) }}</template>
        </el-table-column>
        <el-table-column prop="note" label="备注" />
        <el-table-column label="操作" width="90">
          <template #default="{ row }">
            <el-button text type="danger" size="small" @click="removeRecord(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount, computed, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import {
  startRecord, stopRecord, deleteRecord, getHistory, getStats,
  type TimerMode, type RecordItem, type StatsData,
} from '@/api/timer'
import { listTasks, type TaskItem } from '@/api/task'

const mode = ref<TimerMode>('pomodoro')
const running = ref(false)
const phase = ref<'work' | 'break'>('work')
const cycles = ref(0)
const workMin = ref(25)
const breakMin = ref(5)
const targetMin = ref(25)
const taskId = ref<number | null>(null)
const subject = ref<string | null>(null)
const saveTip = ref('')

const elapsed = ref(0)        // 正计时累计秒
const secondsLeft = ref(0)    // 倒计时剩余秒
const workLeft = ref(0)
const breakLeft = ref(0)
const currentRecordId = ref<number | null>(null)
let timer: number | undefined

const timeText = computed(() => {
  if (mode.value === 'countup') return fmt(elapsed.value)
  if (mode.value === 'countdown') return fmt(secondsLeft.value)
  return fmt(phase.value === 'work' ? workLeft.value : breakLeft.value)
})

const tasks = ref<TaskItem[]>([])
const history = ref<RecordItem[]>([])
const stats = reactive<StatsData>({
  range: 'week', total_seconds: 0, total_hours: 0, session_count: 0,
  by_mode: {}, by_subject: {}, daily: [],
})
const statsRange = ref<'day' | 'week' | 'month' | 'all'>('week')

const pieRef = ref<HTMLElement>()
const barRef = ref<HTMLElement>()
const lineRef = ref<HTMLElement>()
let pieChart: echarts.ECharts | null = null
let barChart: echarts.ECharts | null = null
let lineChart: echarts.ECharts | null = null

function fmt(s: number): string {
  s = Math.max(0, Math.floor(s))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  const mm = String(m).padStart(2, '0')
  const ss = String(sec).padStart(2, '0')
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`
}
function formatDur(sec: number): string {
  sec = sec || 0
  if (sec < 60) return `${sec}秒`
  const m = Math.floor(sec / 60)
  if (m < 60) return `${m}分${sec % 60}秒`
  return `${Math.floor(m / 60)}时${m % 60}分`
}
function modeLabel(m: string): string {
  return ({ pomodoro: '番茄钟', countup: '正计时', countdown: '倒计时', focus: '专注' } as Record<string, string>)[m] || m
}

function resetTimer() {
  stopInterval()
  running.value = false
  elapsed.value = 0
  secondsLeft.value = targetMin.value * 60
  workLeft.value = workMin.value * 60
  breakLeft.value = breakMin.value * 60
  phase.value = 'work'
  cycles.value = 0
  currentRecordId.value = null
  saveTip.value = ''
}

async function start() {
  if (running.value) return
  running.value = true
  saveTip.value = ''
  if (mode.value === 'countup') {
    const rec = await startRecord({ mode: 'countup', subject: subject.value, task_id: taskId.value })
    currentRecordId.value = rec.id
    timer = window.setInterval(tick, 1000)
  } else if (mode.value === 'countdown') {
    const sec = targetMin.value * 60
    secondsLeft.value = sec
    const rec = await startRecord({ mode: 'countdown', planned_duration: sec, subject: subject.value, task_id: taskId.value })
    currentRecordId.value = rec.id
    timer = window.setInterval(tick, 1000)
  } else {
    // pomodoro
    workLeft.value = workMin.value * 60
    phase.value = 'work'
    await beginWork()
    timer = window.setInterval(tick, 1000)
  }
}

async function beginWork() {
  const rec = await startRecord({ mode: 'pomodoro', subject: subject.value, task_id: taskId.value, note: '专注段' })
  currentRecordId.value = rec.id
}

function pause() {
  running.value = false
  stopInterval()
  // 暂停：正计时/倒计时保留记录但先停表，恢复时续接（简化：暂停即结束当前段）
  if (currentRecordId.value && mode.value !== 'pomodoro') {
    stopRecord(currentRecordId.value).then(refreshAfterSave)
  }
}

async function stop() {
  running.value = false
  stopInterval()
  if (currentRecordId.value) {
    await stopRecord(currentRecordId.value)
    saveTip.value = '已保存本次计时'
    currentRecordId.value = null
  }
  await refreshAfterSave()
  resetTimer()
}

async function tick() {
  if (!running.value) return
  if (mode.value === 'countup') {
    elapsed.value++
  } else if (mode.value === 'countdown') {
    secondsLeft.value--
    if (secondsLeft.value <= 0) {
      secondsLeft.value = 0
      running.value = false
      stopInterval()
      if (currentRecordId.value) {
        await stopRecord(currentRecordId.value)
        saveTip.value = '倒计时结束，已保存'
        currentRecordId.value = null
      }
      await refreshAfterSave()
    }
  } else {
    // pomodoro
    if (phase.value === 'work') {
      workLeft.value--
      if (workLeft.value <= 0) {
        workLeft.value = 0
        // 结束一个专注段
        if (currentRecordId.value) await stopRecord(currentRecordId.value)
        currentRecordId.value = null
        cycles.value++
        phase.value = 'break'
        breakLeft.value = breakMin.value * 60
        saveTip.value = `完成第 ${cycles.value} 个番茄 🍅`
      }
    } else {
      breakLeft.value--
      if (breakLeft.value <= 0) {
        breakLeft.value = 0
        phase.value = 'work'
        await beginWork()
      }
    }
  }
}

function stopInterval() {
  if (timer) { clearInterval(timer); timer = undefined }
}

async function refreshAfterSave() {
  await Promise.all([loadHistory(), loadStats()])
}

async function loadHistory() {
  const res = await getHistory({ page: 1, page_size: 30 })
  history.value = res.data
}
async function loadStats() {
  const data = await getStats(statsRange.value)
  Object.assign(stats, data)
  await nextTick()
  renderCharts()
}

function renderCharts() {
  if (pieRef.value && !pieChart) pieChart = echarts.init(pieRef.value)
  if (barRef.value && !barChart) barChart = echarts.init(barRef.value)
  if (lineRef.value && !lineChart) lineChart = echarts.init(lineRef.value)

  const modeNames: Record<string, string> = { pomodoro: '番茄钟', countup: '正计时', countdown: '倒计时', focus: '专注' }
  const modeData = Object.entries(stats.by_mode).map(([k, v]) => ({ name: modeNames[k] || k, value: Math.round((v || 0) / 60) }))
  pieChart?.setOption({
    title: { text: '按模式(分钟)', left: 'center', textStyle: { fontSize: 12 } },
    tooltip: { trigger: 'item' },
    series: [{ type: 'pie', radius: '62%', data: modeData, label: { fontSize: 10 } }],
  })
  const subj = Object.entries(stats.by_subject).map(([k, v]) => ({ name: k, value: Math.round((v || 0) / 60) }))
  barChart?.setOption({
    title: { text: '按科目(分钟)', left: 'center', textStyle: { fontSize: 12 } },
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 10, top: 28, bottom: 20 },
    xAxis: { type: 'category', data: subj.map((s) => s.name), axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: subj.map((s) => s.value), itemStyle: { color: '#0F766E' } }],
  })
  lineChart?.setOption({
    title: { text: '每日时长(分钟)', left: 'center', textStyle: { fontSize: 12 } },
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 10, top: 28, bottom: 20 },
    xAxis: { type: 'category', data: stats.daily.map((d) => d.date.slice(5)), axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value' },
    series: [{ type: 'line', smooth: true, data: stats.daily.map((d) => Math.round(d.seconds / 60)), itemStyle: { color: '#14B8A6' }, areaStyle: { opacity: 0.15 } }],
  })
}

async function removeRecord(row: RecordItem) {
  await deleteRecord(row.id)
  await refreshAfterSave()
}

// 选任务时自动带出科目
function onTaskChange() {
  const t = tasks.value.find((x) => x.id === taskId.value)
  subject.value = t ? t.subject : null
}
watch(taskId, onTaskChange)

onMounted(async () => {
  resetTimer()
  const res = await listTasks({ page: 1, page_size: 100 })
  tasks.value = res.data
  await loadHistory()
  await loadStats()
})
onBeforeUnmount(() => { stopInterval() })
</script>

<style scoped>
.timer-page { }
.timer-card { border-radius: 16px; }
.mode-switch { display: flex; justify-content: center; margin-bottom: 18px; }
.clock { text-align: center; padding: 24px 0; }
.clock.rest { background: rgba(20,184,166,.08); border-radius: 14px; }
.clock-time { font-size: 64px; font-weight: 800; font-variant-numeric: tabular-nums; color: var(--brand-700, #0F766E); letter-spacing: 2px; }
.clock-phase { margin-top: 8px; color: var(--text-muted); font-size: 14px; }
.config { display: flex; flex-wrap: wrap; gap: 16px; justify-content: center; align-items: center; margin: 12px 0 20px; font-size: 14px; color: var(--text-secondary); }
.controls { display: flex; gap: 12px; justify-content: center; }
.save-tip { text-align: center; margin-top: 14px; color: var(--brand-700, #0F766E); font-size: 13px; }
.stats-card { border-radius: 16px; }
.stats-head { display: flex; justify-content: space-between; align-items: center; font-weight: 600; margin-bottom: 12px; }
.stat-big { text-align: center; margin-bottom: 14px; }
.stat-hours { font-size: 48px; font-weight: 800; color: var(--brand-700, #0F766E); }
.stat-hours small { font-size: 18px; margin-left: 4px; }
.stat-sub { color: var(--text-muted); font-size: 13px; }
.chart { height: 170px; }
.chart-line { height: 180px; margin-top: 8px; }
</style>

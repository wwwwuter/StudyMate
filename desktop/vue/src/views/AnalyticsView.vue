<template>
  <div class="analytics-page">
    <!-- 工具条 -->
    <div class="toolbar">
      <el-radio-group v-model="range" size="default" @change="loadReport">
        <el-radio-button label="day">今天</el-radio-button>
        <el-radio-button label="week">本周</el-radio-button>
        <el-radio-button label="month">本月</el-radio-button>
        <el-radio-button label="all">全部</el-radio-button>
      </el-radio-group>

      <div class="toolbar-actions">
        <el-button :icon="Refresh" :loading="loading" @click="loadReport">刷新数据</el-button>
        <el-button
          type="primary"
          :icon="MagicStick"
          :loading="reportLoading"
          @click="genReport"
        >
          生成 AI 学习报告
        </el-button>
      </div>
    </div>

    <!-- KPI 卡片 -->
    <el-row :gutter="16" class="kpi-row">
      <el-col :xs="12" :sm="8" :md="4" v-for="k in kpis" :key="k.label">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-val" :style="{ color: k.color }">{{ k.value }}</div>
          <div class="kpi-label">{{ k.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 空态 -->
    <el-empty
      v-if="empty"
      description="当前范围暂无学习与任务数据，去计时或制定计划后回来查看吧～"
      :image-size="120"
    />

    <!-- 图表区 -->
    <template v-else>
      <el-row :gutter="16">
        <el-col :xs="24" :lg="16">
          <el-card shadow="never" class="chart-card">
            <div class="chart-card-head"><span>每日学习时长</span><em>分钟</em></div>
            <div ref="dailyLineRef" class="chart chart-lg"></div>
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="8">
          <el-card shadow="never" class="chart-card">
            <div class="chart-card-head"><span>计时模式分布</span><em>分钟</em></div>
            <div ref="modePieRef" class="chart chart-lg"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :xs="24" :lg="12">
          <el-card shadow="never" class="chart-card">
            <div class="chart-card-head"><span>各科目实际时长</span><em>分钟</em></div>
            <div ref="subjectBarRef" class="chart chart-md"></div>
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="12">
          <el-card shadow="never" class="chart-card">
            <div class="chart-card-head"><span>计划 vs 实际（按科目）</span><em>分钟</em></div>
            <div ref="planActualBarRef" class="chart chart-md"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :xs="24" :lg="16">
          <el-card shadow="never" class="chart-card">
            <div class="chart-card-head"><span>时段分布（24 小时）</span><em>分钟</em></div>
            <div ref="hourBarRef" class="chart chart-md"></div>
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="8">
          <el-card shadow="never" class="chart-card">
            <div class="chart-card-head"><span>任务完成情况</span><em>已完成 / 未完成</em></div>
            <div ref="taskPieRef" class="chart chart-md"></div>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <!-- AI 学习报告 -->
    <el-card shadow="never" class="report-card" style="margin-top: 16px">
      <div class="report-head">
        <span>AI 学习报告</span>
        <el-tag v-if="summary" :type="summary.source === 'ai' ? 'primary' : 'info'" size="small">
          {{ summary.source === 'ai' ? 'DeepSeek 生成' : '模板总结' }}
        </el-tag>
      </div>
      <div v-if="reportLoading" class="report-loading">
        <el-icon class="is-loading"><Loading /></el-icon> 正在生成报告…
      </div>
      <div v-else-if="summary" class="report-body">{{ summary.text }}</div>
      <el-empty v-else description="点击右上角「生成 AI 学习报告」获取文字总结" :image-size="90" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, MagicStick, Loading } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getReport, generateSummary, type RangeType, type ReportData } from '@/api/analytics'

const PALETTE = ['#0F766E', '#14B8A6', '#0EA5E9', '#F59E0B', '#10B981', '#8B5CF6', '#EF4444', '#64748B']
const MODE_LABELS: Record<string, string> = {
  pomodoro: '番茄钟', countup: '正计时', countdown: '倒计时', focus: '专注',
}

const range = ref<RangeType>('week')
const loading = ref(false)
const reportLoading = ref(false)
const report = ref<ReportData | null>(null)
const summary = ref<{ text: string; source: 'ai' | 'template' } | null>(null)

const empty = computed(
  () => report.value === null || (report.value.total_seconds === 0 && report.value.tasks.total === 0),
)

const kpis = computed(() => {
  const r = report.value
  if (!r) {
    return [
      { label: '总时长', value: '—', color: 'var(--brand-700)' },
      { label: '学习会话', value: '—', color: 'var(--brand-600)' },
      { label: '平均单次', value: '—', color: 'var(--ai-600)' },
      { label: '日均', value: '—', color: 'var(--brand-500)' },
      { label: '连续打卡', value: '—', color: 'var(--warning)' },
      { label: '任务完成率', value: '—', color: 'var(--success)' },
    ]
  }
  return [
    { label: '总时长', value: `${r.total_hours}h`, color: 'var(--brand-700)' },
    { label: '学习会话', value: `${r.session_count}`, color: 'var(--brand-600)' },
    { label: '平均单次(分)', value: `${r.avg_session_minutes}`, color: 'var(--ai-600)' },
    { label: '日均(分)', value: `${r.daily_avg_minutes}`, color: 'var(--brand-500)' },
    { label: '连续打卡(天)', value: `${r.streak}`, color: 'var(--warning)' },
    { label: '任务完成率', value: `${r.tasks.completion_rate}%`, color: 'var(--success)' },
  ]
})

// ---- 图表实例 ----
const dailyLineRef = ref<HTMLElement>()
const modePieRef = ref<HTMLElement>()
const subjectBarRef = ref<HTMLElement>()
const planActualBarRef = ref<HTMLElement>()
const hourBarRef = ref<HTMLElement>()
const taskPieRef = ref<HTMLElement>()
const charts: Record<string, echarts.ECharts | null> = {
  daily: null, mode: null, subject: null, planActual: null, hour: null, task: null,
}

function ensureChart(key: string, el?: HTMLElement): echarts.ECharts | null {
  if (el && !charts[key]) charts[key] = echarts.init(el)
  return charts[key]
}

function renderAll() {
  const r = report.value
  if (!r) return
  nextTick(() => {
    // 1. 每日趋势
    const line = ensureChart('daily', dailyLineRef.value)
    line?.setOption(
      {
        tooltip: { trigger: 'axis' },
        grid: { left: 44, right: 16, top: 20, bottom: 30 },
        xAxis: { type: 'category', data: r.daily.map((d) => d.date.slice(5)), axisLabel: { fontSize: 11 } },
        yAxis: { type: 'value' },
        series: [
          {
            type: 'line', smooth: true,
            data: r.daily.map((d) => Math.round(d.seconds / 60)),
            itemStyle: { color: '#0F766E' }, lineStyle: { width: 3 },
            areaStyle: { color: 'rgba(20,184,166,.16)' },
          },
        ],
      },
      true,
    )

    // 2. 模式分布
    const modeData = Object.entries(r.by_mode).map(([k, v]) => ({
      name: MODE_LABELS[k] || k, value: Math.round((v || 0) / 60),
    }))
    const mode = ensureChart('mode', modePieRef.value)
    mode?.setOption(
      {
        tooltip: { trigger: 'item' },
        legend: { bottom: 0, type: 'scroll' },
        color: PALETTE,
        series: [{ type: 'pie', radius: ['38%', '66%'], center: ['50%', '44%'], data: modeData, label: { fontSize: 11 } }],
      },
      true,
    )

    // 3. 科目实际时长
    const subj = Object.entries(r.by_subject_actual).map(([k, v]) => ({
      name: k, value: Math.round((v || 0) / 60),
    }))
    const subject = ensureChart('subject', subjectBarRef.value)
    subject?.setOption(
      {
        tooltip: { trigger: 'axis' },
        grid: { left: 44, right: 16, top: 20, bottom: 24 },
        xAxis: { type: 'category', data: subj.map((s) => s.name), axisLabel: { fontSize: 11, interval: 0, rotate: subj.length > 5 ? 30 : 0 } },
        yAxis: { type: 'value' },
        series: [{ type: 'bar', data: subj.map((s) => s.value), itemStyle: { color: '#14B8A6', borderRadius: [6, 6, 0, 0] } }],
      },
      true,
    )

    // 4. 计划 vs 实际（按科目，分钟）
    const subjects = Array.from(new Set([...Object.keys(r.by_subject_actual), ...Object.keys(r.by_subject_planned)]))
    const actualMin = subjects.map((s) => Math.round((r.by_subject_actual[s] || 0) / 60))
    const plannedMin = subjects.map((s) => r.by_subject_planned[s] || 0)
    const pa = ensureChart('planActual', planActualBarRef.value)
    pa?.setOption(
      {
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        legend: { bottom: 0 },
        grid: { left: 44, right: 16, top: 20, bottom: 36 },
        xAxis: { type: 'category', data: subjects, axisLabel: { fontSize: 11, interval: 0, rotate: subjects.length > 5 ? 30 : 0 } },
        yAxis: { type: 'value' },
        series: [
          { name: '实际', type: 'bar', data: actualMin, itemStyle: { color: '#0F766E', borderRadius: [6, 6, 0, 0] } },
          { name: '计划', type: 'bar', data: plannedMin, itemStyle: { color: '#0EA5E9', borderRadius: [6, 6, 0, 0] } },
        ],
      },
      true,
    )

    // 5. 时段分布 24h
    const hour = ensureChart('hour', hourBarRef.value)
    hour?.setOption(
      {
        tooltip: { trigger: 'axis' },
        grid: { left: 44, right: 16, top: 20, bottom: 28 },
        xAxis: { type: 'category', data: r.hour_distribution.map((h) => `${h.hour}`), axisLabel: { fontSize: 10, interval: 1 } },
        yAxis: { type: 'value' },
        series: [{ type: 'bar', data: r.hour_distribution.map((h) => Math.round(h.seconds / 60)), itemStyle: { color: '#0D9488', borderRadius: [3, 3, 0, 0] } }],
      },
      true,
    )

    // 6. 任务完成
    const t = r.tasks
    const task = ensureChart('task', taskPieRef.value)
    task?.setOption(
      {
        tooltip: { trigger: 'item' },
        legend: { bottom: 0 },
        color: ['#10B981', '#F59E0B'],
        series: [
          {
            type: 'pie', radius: ['40%', '66%'], center: ['50%', '44%'],
            data: [
              { name: '已完成', value: t.done },
              { name: '未完成', value: t.pending },
            ],
            label: { formatter: '{b}\n{c}', fontSize: 11 },
          },
        ],
      },
      true,
    )
  })
}

async function loadReport() {
  loading.value = true
  try {
    report.value = await getReport(range.value)
    summary.value = null // 数据变化后，旧报告失效
    renderAll()
  } catch (e) {
    ElMessage.error((e as Error).message || '加载报告失败')
  } finally {
    loading.value = false
  }
}

async function genReport() {
  reportLoading.value = true
  try {
    const res = await generateSummary({ range: range.value })
    summary.value = { text: res.text, source: res.source }
  } catch (e) {
    ElMessage.error((e as Error).message || '生成报告失败')
  } finally {
    reportLoading.value = false
  }
}

function onResize() {
  Object.values(charts).forEach((c) => c?.resize())
}

onMounted(() => {
  loadReport()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  Object.values(charts).forEach((c) => c?.dispose())
})
</script>

<style scoped>
.analytics-page { }
.toolbar { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 16px; }
.toolbar-actions { display: flex; gap: 10px; }

.kpi-row { margin-bottom: 16px; }
.kpi-card { border-radius: 14px; text-align: center; }
.kpi-val { font-size: 26px; font-weight: 800; font-variant-numeric: tabular-nums; line-height: 1.2; }
.kpi-label { margin-top: 4px; font-size: 13px; color: var(--text-muted); }

.chart-card { border-radius: 14px; }
.chart-card-head { display: flex; justify-content: space-between; align-items: baseline; font-weight: 600; margin-bottom: 8px; }
.chart-card-head em { font-style: normal; font-size: 12px; color: var(--text-muted); font-weight: 400; }
.chart { width: 100%; }
.chart-lg { height: 300px; }
.chart-md { height: 280px; }

.report-card { border-radius: 14px; }
.report-head { display: flex; align-items: center; gap: 10px; font-weight: 600; margin-bottom: 12px; }
.report-body { white-space: pre-wrap; line-height: 1.8; color: var(--text); font-size: 14px; }
.report-loading { color: var(--text-muted); display: flex; align-items: center; gap: 8px; }
</style>

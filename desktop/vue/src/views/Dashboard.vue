<template>
  <div class="dashboard">
    <!-- 欢迎横幅 -->
    <section class="hero">
      <div class="hero-text">
        <p class="hero-hello">下午好，考研同学 👋</p>
        <h1>今天也要稳住节奏，离目标更近一步。</h1>
        <p class="hero-sub">已连续打卡 <b>12</b> 天 · 本周计划完成 <b>68%</b></p>
        <el-button type="primary" size="large" round class="hero-btn">
          <el-icon><VideoPlay /></el-icon> 开始今日学习
        </el-button>
      </div>
      <div class="hero-deco">
        <div class="ring r1"></div>
        <div class="ring r2"></div>
        <div class="ring r3"></div>
      </div>
    </section>

    <!-- 统计卡 -->
    <section class="stat-row">
      <div v-for="s in stats" :key="s.label" class="stat-card">
        <div class="stat-icon" :style="{ background: s.bg, color: s.color }">
          <el-icon :size="22"><component :is="s.icon" /></el-icon>
        </div>
        <div class="stat-meta">
          <div class="stat-value">{{ s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </div>
        <div class="stat-trend" :class="s.up ? 'up' : 'down'">
          <el-icon><CaretTop v-if="s.up" /><CaretBottom v-else /></el-icon>
          {{ s.trend }}
        </div>
      </div>
    </section>

    <!-- 图表 + 计划 -->
    <section class="mid-row">
      <el-card class="chart-card" shadow="never">
        <template #header>
          <div class="card-head">
            <span class="card-title">近 7 日学习时长</span>
            <el-tag size="small" type="success" effect="light">单位：小时</el-tag>
          </div>
        </template>
        <div ref="chartEl" class="chart"></div>
      </el-card>

      <el-card class="plan-card" shadow="never">
        <template #header>
          <div class="card-head">
            <span class="card-title">今日计划</span>
            <el-button text type="primary" size="small">查看全部</el-button>
          </div>
        </template>
        <ul class="plan-list">
          <li v-for="(p, i) in plans" :key="i" :class="{ done: p.done }">
            <el-checkbox v-model="p.done" />
            <div class="plan-body">
              <div class="plan-name">{{ p.name }}</div>
              <div class="plan-tag">
                <el-tag size="small" :type="p.type" effect="plain">{{ p.cat }}</el-tag>
                <span class="plan-time">{{ p.time }}</span>
              </div>
            </div>
          </li>
        </ul>
      </el-card>
    </section>

    <!-- AI 助手卡 -->
    <section>
      <el-card class="ai-card" shadow="never">
        <div class="ai-inner">
          <div class="ai-badge"><el-icon><MagicStick /></el-icon> AI 学习助手</div>
          <h3>卡住的知识点，直接问它</h3>
          <p>让 AI 帮你梳理考点、生成错题解析、定制复习计划。</p>
          <div class="ai-actions">
            <el-button color="#0EA5E9" round>发起对话</el-button>
            <el-button round plain color="#0EA5E9">生成今日复习清单</el-button>
          </div>
        </div>
      </el-card>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import {
  Timer, List, Medal, Document, VideoPlay,
  CaretTop, CaretBottom, MagicStick,
} from '@element-plus/icons-vue'

const stats = [
  { label: '累计学习时长', value: '328 h', trend: '12%', up: true,  icon: Timer,   color: '#0F766E', bg: '#E7F1F0' },
  { label: '今日任务',     value: '5 / 8', trend: '2',    up: true,  icon: List,    color: '#0EA5E9', bg: '#E0F2FE' },
  { label: '连续打卡',     value: '12 天', trend: '3 天', up: true,  icon: Medal,   color: '#F59E0B', bg: '#FEF3C7' },
  { label: '待复习资料',   value: '23',    trend: '5',    up: false, icon: Document,color: '#EF4444', bg: '#FEE2E2' },
]

const plans = ref([
  { name: '英语阅读理解真题 2 篇', cat: '英语', type: 'warning' as const, time: '09:00', done: true },
  { name: '数学高数·中值定理专题', cat: '数学', type: 'primary' as const, time: '14:00', done: false },
  { name: '政治·马原重难点复盘',   cat: '政治', type: 'success' as const, time: '16:30', done: false },
  { name: '专业课·数据结构刷题',   cat: '专业课', type: 'info' as const, time: '19:00', done: false },
])

const chartEl = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

onMounted(() => {
  if (!chartEl.value) return
  chart = echarts.init(chartEl.value)
  chart.setOption({
    grid: { left: 36, right: 16, top: 24, bottom: 28 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'line' }, backgroundColor: '#fff', borderColor: '#E3EBE8' },
    xAxis: {
      type: 'category',
      data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
      axisLine: { lineStyle: { color: '#E3EBE8' } },
      axisLabel: { color: '#5B6B66' },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#F1F6F4' } },
      axisLabel: { color: '#93A39D' },
    },
    series: [{
      name: '学习时长',
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      data: [4.2, 5.1, 3.8, 6.0, 5.5, 7.2, 4.9],
      lineStyle: { width: 3, color: '#0F766E' },
      itemStyle: { color: '#0F766E' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(15,118,110,.28)' },
          { offset: 1, color: 'rgba(15,118,110,.02)' },
        ]),
      },
    }],
  })
  window.addEventListener('resize', () => chart?.resize())
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', () => chart?.resize())
  chart?.dispose()
})
</script>

<style scoped>
.dashboard { display: flex; flex-direction: column; gap: 20px; }

/* 横幅 */
.hero {
  position: relative; overflow: hidden;
  background: linear-gradient(120deg, #0F766E 0%, #14B8A6 100%);
  border-radius: var(--radius-lg);
  padding: 28px 32px;
  color: #fff;
}
.hero-hello { margin: 0; opacity: .85; font-size: 14px; }
.hero-text h1 { margin: 6px 0 8px; font-size: 24px; font-weight: 700; }
.hero-sub { margin: 0 0 18px; opacity: .9; font-size: 14px; }
.hero-sub b { font-weight: 700; }
.hero-btn { background: #fff; color: #0F766E; border: none; font-weight: 600; }
.hero-deco { position: absolute; right: -40px; top: -40px; }
.ring { position: absolute; border: 2px solid rgba(255,255,255,.18); border-radius: 50%; }
.r1 { width: 180px; height: 180px; right: 60px; top: 20px; }
.r2 { width: 120px; height: 120px; right: 150px; top: 90px; }
.r3 { width: 70px;  height: 70px;  right: 30px; top: 130px; }

/* 统计卡 */
.stat-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px;
  display: flex; align-items: center; gap: 14px;
  box-shadow: var(--shadow-sm);
}
.stat-icon { width: 46px; height: 46px; border-radius: 12px; display: grid; place-items: center; flex-shrink: 0; }
.stat-value { font-size: 22px; font-weight: 700; color: var(--text-strong); line-height: 1.2; }
.stat-label { font-size: 12px; color: var(--text-muted); }
.stat-trend { margin-left: auto; font-size: 12px; display: flex; align-items: center; gap: 2px; }
.stat-trend.up { color: var(--success); }
.stat-trend.down { color: var(--danger); }

/* 中部 */
.mid-row { display: grid; grid-template-columns: 1.6fr 1fr; gap: 16px; }
.card-head { display: flex; align-items: center; justify-content: space-between; }
.card-title { font-weight: 600; color: var(--text-strong); }
.chart-card, .plan-card { border-radius: var(--radius); }
.chart { height: 280px; }

.plan-list { list-style: none; margin: 0; padding: 0; }
.plan-list li {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 4px;
  border-bottom: 1px solid var(--bg-soft);
}
.plan-list li:last-child { border-bottom: none; }
.plan-list li.done .plan-name { text-decoration: line-through; color: var(--text-muted); }
.plan-body { flex: 1; }
.plan-name { font-size: 14px; color: var(--text); }
.plan-tag { display: flex; align-items: center; gap: 8px; margin-top: 2px; }
.plan-time { font-size: 12px; color: var(--text-muted); }

/* AI 卡 */
.ai-card { border-radius: var(--radius-lg); border: none; background: linear-gradient(120deg, #E0F2FE 0%, #ECFDF5 100%); }
.ai-inner { padding: 8px 4px; }
.ai-badge {
  display: inline-flex; align-items: center; gap: 6px;
  background: #0EA5E9; color: #fff;
  padding: 4px 12px; border-radius: 999px; font-size: 12px; font-weight: 600;
}
.ai-inner h3 { margin: 14px 0 6px; color: var(--text-strong); }
.ai-inner p { margin: 0 0 16px; color: var(--text-secondary); font-size: 14px; }
.ai-actions { display: flex; gap: 12px; }
</style>

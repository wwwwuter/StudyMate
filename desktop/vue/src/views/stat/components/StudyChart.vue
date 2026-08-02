<template>
  <div class="chart-card">
    <div class="block-title">{{ title }}</div>
    <div ref="el" class="chart" />
    <div v-if="!hasData" class="chart-empty">暂无数据</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { StatSubject, TrendPoint } from '@/api/stat'
import { toMinutes } from '../format'

const props = defineProps<{
  type: 'pie' | 'line'
  title?: string
  data: StatSubject[] | TrendPoint[]
}>()

const palette = ['#0F766E', '#14B8A6', '#34D399', '#60A5FA', '#F59E0B', '#F472B6', '#A78BFA', '#94A3B8']

const el = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null

const hasData = computed(() => {
  const arr = props.data as Array<{ time: number }>
  return Array.isArray(arr) && arr.length > 0 && arr.some((d) => (d.time || 0) > 0)
})

function fmtMin(sec: number): string {
  const m = toMinutes(sec)
  return m >= 60 ? `${(m / 60).toFixed(1)}小时` : `${m}分钟`
}

function buildOption(): echarts.EChartsOption {
  if (props.type === 'pie') {
    const items = (props.data as StatSubject[]).map((d) => ({ name: d.name, value: d.time }))
    return {
      tooltip: {
        trigger: 'item',
        formatter: (p: any) => `${p.name}<br/>${fmtMin(p.value)}（${p.percent}%）`,
      },
      legend: { bottom: 0, type: 'scroll', textStyle: { color: '#6b7280' } },
      series: [
        {
          type: 'pie',
          radius: ['42%', '68%'],
          center: ['50%', '46%'],
          avoidLabelOverlap: true,
          itemStyle: { borderColor: '#fff', borderWidth: 2 },
          label: { show: false },
          data: items,
          color: palette,
        },
      ],
    }
  }
  const items = props.data as TrendPoint[]
  return {
    tooltip: { trigger: 'axis', formatter: (ps: any) => `${ps[0].axisValue}<br/>${fmtMin(ps[0].value)}` },
    grid: { left: 46, right: 18, top: 18, bottom: 28 },
    xAxis: {
      type: 'category',
      data: items.map((d) => d.date),
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisLabel: { color: '#9ca3af', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: '分钟',
      nameTextStyle: { color: '#9ca3af' },
      splitLine: { lineStyle: { color: '#f1f5f9' } },
      axisLabel: { color: '#9ca3af', fontSize: 11 },
    },
    series: [
      {
        type: 'line',
        smooth: true,
        showSymbol: false,
        symbol: 'circle',
        symbolSize: 5,
        data: items.map((d) => toMinutes(d.time)),
        lineStyle: { width: 2.5, color: '#0F766E' },
        itemStyle: { color: '#0F766E' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(15,118,110,0.28)' },
            { offset: 1, color: 'rgba(15,118,110,0.02)' },
          ]),
        },
      },
    ],
  }
}

function render() {
  if (!el.value) return
  if (!chart) chart = echarts.init(el.value)
  chart.setOption(buildOption(), true)
  nextTick(() => chart?.resize())
}

function onResize() {
  chart?.resize()
}

onMounted(() => {
  nextTick(render)
  window.addEventListener('resize', onResize)
  if (typeof ResizeObserver !== 'undefined' && el.value) {
    resizeObserver = new ResizeObserver(() => chart?.resize())
    resizeObserver.observe(el.value)
  }
})
watch(() => [props.type, props.data], () => render(), { deep: true })
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  resizeObserver?.disconnect()
  resizeObserver = null
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.chart-card {
  background: #fff;
  border: 1px solid #eef1f4;
  border-radius: 14px;
  padding: 16px 18px;
  box-shadow: 0 2px 10px rgba(15, 118, 110, 0.05);
  position: relative;
}
.block-title {
  font-size: 15px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 10px;
}
.chart {
  width: 100%;
  height: 260px;
}
.chart-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: #aab2bf;
  pointer-events: none;
}
</style>

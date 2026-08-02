<template>
  <div class="mode-card">
    <div class="block-title">{{ title }}</div>
    <div ref="el" class="chart" />
    <div v-if="!hasData" class="chart-empty">暂无计时数据</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { ModeItem } from '@/api/stat'
import { fmtDuration } from '../format'

const props = defineProps<{
  title?: string
  data: ModeItem[]
}>()

const palette = ['#0F766E', '#14B8A6', '#34D399', '#60A5FA', '#F59E0B', '#F472B6', '#A78BFA', '#94A3B8']

const el = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null

const hasData = computed(() => Array.isArray(props.data) && props.data.length > 0)

function buildOption(): echarts.EChartsOption {
  const items = props.data.map((d) => ({ name: d.name, value: d.value, count: d.count }))
  return {
    tooltip: {
      trigger: 'item',
      formatter: (p: any) =>
        `${p.name}<br/>${fmtDuration(p.value)}（${p.percent}%）<br/>计时 ${p.data.count} 次`,
    },
    legend: { bottom: 0, type: 'scroll', textStyle: { color: '#6b7280' } },
    series: [
      {
        type: 'pie',
        radius: ['42%', '68%'],
        center: ['50%', '46%'],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: '#fff', borderWidth: 2 },
        label: {
          show: true,
          formatter: '{b}\n{d}%',
          color: '#475569',
          fontSize: 12,
        },
        data: items,
        color: palette,
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
watch(() => props.data, () => render(), { deep: true })
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  resizeObserver?.disconnect()
  resizeObserver = null
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.mode-card {
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

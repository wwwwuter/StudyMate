<template>
  <div class="stats-page">
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>本周学习时长（小时）</span>
          </template>
          <div class="chart-container">
            <v-chart :option="dailyChartOption" style="height: 300px" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>每日任务完成率</span>
          </template>
          <div class="chart-container">
            <v-chart :option="completionChartOption" style="height: 300px" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="24">
        <el-card>
          <template #header>
            <span>AI 学习总结</span>
          </template>
          <div class="ai-summary">
            <el-button type="primary" :loading="summaryLoading" @click="generateSummary">
              生成今日总结
            </el-button>
            <div v-if="summary" class="summary-content">
              <div v-html="renderedSummary"></div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { use } from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { recordApi, aiApi, taskApi } from '@/api'
import dayjs from 'dayjs'

use([BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const dailyChartOption = ref({})
const completionChartOption = ref({})
const summaryLoading = ref(false)
const summary = ref('')

const renderedSummary = computed(() => {
  if (!summary.value) return ''
  return summary.value.replace(/\n/g, '<br>')
})

onMounted(async () => {
  try {
    const weeklyRes: any = await recordApi.weeklyStats()
    const data = weeklyRes.data.daily_seconds || {}

    const days = Object.keys(data).sort()
    const hours = days.map((d) => Math.round((data[d] || 0) / 36) / 100)

    dailyChartOption.value = {
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: days },
      yAxis: { type: 'value', name: '小时' },
      series: [{ type: 'bar', data: hours, itemStyle: { color: '#409eff' } }],
    }
  } catch (err) {
    console.error('加载统计失败:', err)
  }
})

async function generateSummary() {
  summaryLoading.value = true
  try {
    const res: any = await aiApi.dailySummary()
    summary.value = res.data.output_data
  } catch (err: any) {
    summary.value = 'AI 总结生成失败，请检查 DeepSeek API 配置'
  } finally {
    summaryLoading.value = false
  }
}
</script>

<style scoped>
.chart-container {
  width: 100%;
}

.ai-summary {
  text-align: center;
}

.summary-content {
  margin-top: 16px;
  text-align: left;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
  line-height: 1.8;
  white-space: pre-wrap;
}
</style>
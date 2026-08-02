<template>
  <div class="stat-page">
    <el-row :gutter="16" class="section">
      <el-col :xs="12" :sm="6">
        <StatCard label="累计学习时间" :value="fmtDuration(data?.total_time ?? 0)" />
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard label="累计计时次数" :value="`${data?.total_sessions ?? 0} 次`" />
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard label="累计完成任务" :value="`${data?.completed_tasks ?? 0}`" />
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard label="连续学习天数" :value="`${data?.continuous_days ?? 0} 天`" />
      </el-col>
    </el-row>

    <el-row :gutter="16" class="section">
      <el-col :xs="24">
        <StudyChart type="line" title="学习趋势（最近30天）" :data="data?.trend ?? []" />
      </el-col>
    </el-row>

    <el-row :gutter="16" class="section">
      <el-col :xs="24">
        <StudyChart type="pie" title="科目投入比例" :data="data?.subjects ?? []" />
      </el-col>
    </el-row>

    <el-row :gutter="16" class="section">
      <el-col :xs="24">
        <TimerModeChart title="计时模式分布" :data="data?.mode_distribution ?? []" />
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import StatCard from './components/StatCard.vue'
import StudyChart from './components/StudyChart.vue'
import TimerModeChart from './components/TimerModeChart.vue'
import { getAllStat, type AllStat as AllStatData } from '@/api/stat'
import { fmtDuration } from './format'

const data = ref<AllStatData | null>(null)

async function load() {
  try {
    const res = await getAllStat()
    data.value = res.data
  } catch {
    data.value = null
  }
}

onMounted(load)
</script>

<style scoped>
.stat-page {
  max-width: 1100px;
  margin: 0 auto;
}
.section {
  margin-bottom: 16px;
}
</style>

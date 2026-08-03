<template>
  <div class="stat-page">
    <el-row :gutter="16" class="section">
      <el-col :xs="12" :sm="6">
        <StatCard label="计划完成学习" :value="fmtDuration(data?.total_time ?? 0)" />
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard label="实际投入" :value="fmtDuration(data?.actual_total ?? 0)" hint="真实计时" />
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard label="额外投入" :value="`+${fmtDuration(data?.extra_total ?? 0)}`" hint="超计划部分" />
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
      <el-col :xs="12" :sm="6">
        <StatCard label="计划执行率" :value="`${data?.plan_execution_rate ?? 0}%`" />
      </el-col>
    </el-row>

    <!-- 计划版本执行情况 -->
    <el-row v-if="data?.plan_stats?.length" :gutter="16" class="section">
      <el-col :xs="24">
        <div class="plan-stat-card">
          <div class="plan-stat-title">计划执行情况</div>
          <div v-for="p in data.plan_stats" :key="p.plan_id" class="plan-stat-row">
            <span class="ps-name">{{ p.plan_name }} <span class="ps-ver">v{{ p.version }}</span></span>
            <el-progress
              :percentage="p.rate"
              :stroke-width="8"
              class="ps-bar"
              :color="p.rate >= 70 ? '#0F766E' : p.rate >= 40 ? '#F59E0B' : '#EF4444'"
            />
            <span class="ps-count">{{ p.done }}/{{ p.total }} 已完成</span>
          </div>
        </div>
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
.plan-stat-card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 16px 18px;
}
.plan-stat-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-strong, #1f2937);
  margin-bottom: 12px;
}
.plan-stat-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 10px;
}
.plan-stat-row:last-child {
  margin-bottom: 0;
}
.ps-name {
  min-width: 160px;
  font-size: 13px;
  color: var(--text-strong, #1f2937);
}
.ps-ver {
  font-size: 11px;
  color: var(--text-muted, #6b7280);
  background: var(--el-fill-color-light);
  border-radius: 4px;
  padding: 1px 6px;
}
.ps-bar {
  flex: 1;
  max-width: 420px;
}
.ps-count {
  font-size: 12px;
  color: var(--text-muted, #6b7280);
  min-width: 70px;
}
</style>

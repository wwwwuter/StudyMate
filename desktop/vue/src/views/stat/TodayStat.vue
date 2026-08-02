<template>
  <div class="stat-page">
    <el-row :gutter="16" class="section">
      <el-col :xs="24" :sm="8">
        <StatCard label="今日学习时长" :value="fmtDuration(data?.study_time ?? 0)" />
      </el-col>
      <el-col :xs="24" :sm="8">
        <StatCard label="今日任务完成" :value="`${data?.task_completed ?? 0} / ${data?.task_total ?? 0}`" />
      </el-col>
      <el-col :xs="24" :sm="8">
        <StatCard label="今日完成率" :value="`${data?.completion_rate ?? 0}%`" />
      </el-col>
    </el-row>

    <el-row :gutter="16" class="section">
      <el-col :xs="24" :lg="13">
        <TaskTimeline :tasks="data?.tasks ?? []" @open="openTask" />
      </el-col>
      <el-col :xs="24" :lg="11">
        <StudyChart type="pie" title="今日科目学习比例" :data="data?.subjects ?? []" />
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onActivated } from 'vue'
import { useRouter } from 'vue-router'
import StatCard from './components/StatCard.vue'
import TaskTimeline from './components/TaskTimeline.vue'
import StudyChart from './components/StudyChart.vue'
import { getTodayStat, type TodayStat as TodayStatData, type TodayTaskItem } from '@/api/stat'
import { fmtDuration } from './format'

const router = useRouter()
const data = ref<TodayStatData | null>(null)

async function load() {
  try {
    const res = await getTodayStat()
    data.value = res.data
  } catch {
    data.value = null
  }
}

function openTask(t: TodayTaskItem) {
  router.push({ path: '/timer', query: { taskId: t.id } })
}

onMounted(load)
// 从计时页返回时刷新（任务完成率实时更新）
onActivated(load)
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

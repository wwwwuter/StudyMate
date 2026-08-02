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

    <!-- AI 学习建议（有 Key 走 AI，无 Key 走规则模板降级） -->
    <el-row :gutter="16" class="section">
      <el-col :xs="24">
        <div class="advice-card">
          <div class="advice-head">
            <div class="advice-title">
              <el-icon class="advice-icon"><MagicStick /></el-icon>
              AI 学习建议
              <el-tag
                v-if="advice"
                size="small"
                :type="advice.source === 'ai' ? 'success' : 'info'"
                round
              >
                {{ advice.source === 'ai' ? 'AI 生成' : '规则生成' }}
              </el-tag>
            </div>
            <el-button size="small" :loading="adviceLoading" @click="loadAdvice">
              {{ advice ? '重新生成' : '生成建议' }}
            </el-button>
          </div>

          <el-skeleton v-if="adviceLoading && !advice" :rows="3" animated />

          <template v-else-if="advice">
            <p class="advice-summary">{{ advice.summary }}</p>
            <div class="advice-row problem">
              <span class="advice-label">问题</span>
              <span>{{ advice.problems || '无' }}</span>
            </div>
            <div class="advice-row suggestion">
              <span class="advice-label">建议</span>
              <span>{{ advice.suggestions || '无' }}</span>
            </div>
            <p v-if="advice.source === 'template'" class="advice-hint">
              当前为规则生成建议；到「设置」页填入 API Key 后可获得更智能的个性化分析。
            </p>
          </template>

          <el-empty v-else description="建议生成失败，请重试" :image-size="48" />
        </div>
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
import { MagicStick } from '@element-plus/icons-vue'
import StatCard from './components/StatCard.vue'
import TaskTimeline from './components/TaskTimeline.vue'
import StudyChart from './components/StudyChart.vue'
import { getTodayStat, type TodayStat as TodayStatData, type TodayTaskItem } from '@/api/stat'
import { analyzeToday, type StudyAdvice } from '@/api/ai'
import { fmtDuration } from './format'

const router = useRouter()
const data = ref<TodayStatData | null>(null)
const advice = ref<StudyAdvice | null>(null)
const adviceLoading = ref(false)

async function load() {
  try {
    const res = await getTodayStat()
    data.value = res.data
  } catch {
    data.value = null
  }
}

async function loadAdvice() {
  adviceLoading.value = true
  try {
    const res = await analyzeToday()
    advice.value = res.data
  } catch {
    advice.value = null
  } finally {
    adviceLoading.value = false
  }
}

function openTask(t: TodayTaskItem) {
  router.push({ path: '/timer', query: { taskId: t.id } })
}

onMounted(() => {
  load()
  loadAdvice() // 进入页面自动生成一次建议
})
// 从计时页返回时刷新（任务完成率实时更新）；建议保留上次结果，可点「重新生成」
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
.advice-card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 16px 18px;
}
.advice-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.advice-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-strong, #1f2937);
}
.advice-icon {
  color: #0f766e;
  font-size: 17px;
}
.advice-summary {
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-strong, #1f2937);
  line-height: 1.7;
}
.advice-row {
  display: flex;
  gap: 8px;
  font-size: 13px;
  line-height: 1.7;
  margin-bottom: 8px;
  padding: 8px 12px;
  border-radius: 6px;
}
.advice-label {
  flex-shrink: 0;
  font-weight: 600;
}
.advice-row.problem {
  background: #fef3c7;
  color: #92400e;
}
.advice-row.suggestion {
  background: #d1fae5;
  color: #065f46;
}
.advice-hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--text-muted, #6b7280);
}
</style>

<template>
  <div class="stat-page">
    <el-row :gutter="16" class="section">
      <el-col :xs="12" :sm="6">
        <StatCard
          label="计划有效学习"
          :value="fmtDuration(data?.study_time ?? 0)"
          :hint="`实际投入 ${fmtDuration((data?.study_time ?? 0) + (data?.extra_time ?? 0))}`"
        />
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard label="额外学习" :value="fmtDuration(data?.extra_time ?? 0)" hint="超计划部分" />
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard label="今日任务完成" :value="`${data?.task_completed ?? 0} / ${data?.task_total ?? 0}`" />
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard label="今日完成率" :value="`${data?.completion_rate ?? 0}%`" />
      </el-col>
    </el-row>

    <!-- 当前任务（今日最早未完成） -->
    <el-row v-if="data?.current_task" :gutter="16" class="section">
      <el-col :xs="24">
        <div class="current-task" @click="openTask(data!.current_task!)">
          <el-icon class="ct-icon"><Timer /></el-icon>
          <span class="ct-label">当前任务</span>
          <b>{{ data.current_task.subject }}</b>
          <span class="ct-content">{{ data.current_task.content }}</span>
          <span v-if="data.current_task.start_time" class="ct-time">
            {{ data.current_task.start_time }}-{{ data.current_task.end_time || '…' }}
          </span>
          <span class="ct-go">去计时 →</span>
        </div>
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
            <el-button size="small" :loading="adviceLoading" @click="loadAdvice(true)">
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
            <div v-if="advice.deviation?.length" class="advice-row deviation">
              <span class="advice-label">计划偏差</span>
              <span class="dev-list">
                <span v-for="d in advice.deviation" :key="d.subject" class="dev-item">
                  「{{ d.subject }}」近 7 天完成率 {{ d.rate }}%（{{ d.done }}/{{ d.total }}）
                </span>
              </span>
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
import { MagicStick, Timer } from '@element-plus/icons-vue'
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

const ADVICE_CACHE_PREFIX = 'study_advice_'
function todayKey() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
function loadCachedAdvice(): StudyAdvice | null {
  try {
    const raw = localStorage.getItem(ADVICE_CACHE_PREFIX + todayKey())
    return raw ? (JSON.parse(raw) as StudyAdvice) : null
  } catch {
    return null
  }
}
function saveCachedAdvice(a: StudyAdvice) {
  try { localStorage.setItem(ADVICE_CACHE_PREFIX + todayKey(), JSON.stringify(a)) } catch { /* ignore */ }
}

async function loadAdvice(force = false) {
  // 进入页面不自动调 API：今日已有缓存则直接渲染（点「重新生成」才重跑）
  if (!force) {
    const cached = loadCachedAdvice()
    if (cached) {
      advice.value = cached
      return
    }
  }
  adviceLoading.value = true
  try {
    const res = await analyzeToday()
    advice.value = res.data
    saveCachedAdvice(res.data)
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
.current-task {
  display: flex;
  align-items: center;
  gap: 10px;
  background: linear-gradient(90deg, rgba(15,118,110,.08), rgba(15,118,110,.03));
  border: 1px solid rgba(15,118,110,.25);
  border-radius: 8px;
  padding: 12px 16px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-strong, #1f2937);
}
.current-task:hover {
  background: linear-gradient(90deg, rgba(15,118,110,.14), rgba(15,118,110,.06));
}
.ct-icon {
  color: #0f766e;
  font-size: 16px;
}
.ct-label {
  color: #0f766e;
  font-weight: 600;
}
.ct-content {
  color: var(--text-secondary, #4b5563);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ct-time {
  font-size: 12px;
  color: var(--text-muted, #6b7280);
}
.ct-go {
  margin-left: auto;
  color: #0f766e;
  font-weight: 600;
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
.advice-row.deviation {
  background: #fee2e2;
  color: #991b1b;
}
.dev-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.advice-hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--text-muted, #6b7280);
}
</style>

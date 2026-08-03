<template>
  <div class="dashboard">
    <!-- 概览卡片 -->
    <el-row :gutter="16">
      <el-col :xs="24" :sm="8">
        <el-card shadow="never" class="ov-card">
          <div class="ov-label">今日累计学习</div>
          <div class="ov-value">{{ stats ? stats.total_hours : 0 }}<small>h</small></div>
          <div class="ov-sub">{{ stats ? stats.session_count : 0 }} 次计时</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8">
        <el-card shadow="never" class="ov-card">
          <div class="ov-label">今日计划完成率</div>
          <div class="ov-value">{{ Math.round((stats ? stats.completion_rate : 0) * 100) }}<small>%</small></div>
          <el-progress
            :percentage="Math.round((stats ? stats.completion_rate : 0) * 100)"
            :stroke-width="8"
            class="ov-prog"
          />
          <div class="ov-sub">{{ stats ? stats.task_done : 0 }} / {{ stats ? stats.task_total : 0 }} 完成</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8">
        <el-card shadow="never" class="ov-card">
          <div class="ov-label">当前任务</div>
          <template v-if="current">
            <div class="ov-value sm">{{ current.task ? current.task.subject : '自由计时' }}</div>
            <div class="ov-sub">{{ liveElapsed }} 进行中</div>
          </template>
          <template v-else>
            <div class="ov-value sm muted">暂无</div>
            <div class="ov-sub">去计时页开始</div>
          </template>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :xs="24" :lg="14">
        <el-card shadow="never" class="plan-card">
          <div class="card-head">
            <span>今日计划</span>
            <el-button text size="small" @click="goTasks">查看时间轴 →</el-button>
          </div>
          <div v-if="!tasks.length" class="empty">今天还没有计划，去「上传计划」让 AI 帮你排期吧。</div>
          <ul v-else class="plan-list">
            <li v-for="t in tasks" :key="t.id" class="plan-item" :class="{ done: t.status === 'done', cancelled: t.status === 'cancelled' }">
              <span class="p-time">{{ t.start_time || '未排时' }}</span>
              <span class="p-subj">{{ t.subject }}</span>
              <span class="p-content">{{ t.content }}</span>
              <el-button
                v-if="t.status === 'pending'"
                size="small" type="primary" plain
                @click="startTask(t)"
              >开始计时</el-button>
              <el-tag v-else size="small" :type="t.status === 'done' ? 'success' : 'info'">
                {{ t.status === 'done' ? '已完成' : '已取消' }}
              </el-tag>
            </li>
          </ul>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="10">
        <el-card shadow="never" class="quick-card">
          <div class="card-head"><span>快捷操作</span></div>
          <div class="quick-grid">
            <el-button class="quick-btn" @click="goUpload">
              <el-icon><Upload /></el-icon> 上传计划
            </el-button>
            <el-button class="quick-btn" @click="goTimer">
              <el-icon><Timer /></el-icon> 开始计时
            </el-button>
            <el-button class="quick-btn" @click="goStats">
              <el-icon><DataLine /></el-icon> 学习记录
            </el-button>
            <el-button class="quick-btn" @click="goSettings">
              <el-icon><Setting /></el-icon> AI 设置
            </el-button>
          </div>
          <el-alert
            v-if="current"
            type="success"
            :closable="false"
            class="running-tip"
            @close="goTimer"
          >
            正在计时：{{ current.task ? current.task.subject : '自由计时' }}（{{ liveElapsed }}）
            <el-button text size="small" type="success" @click="goTimer">前往</el-button>
          </el-alert>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Upload, Timer, DataLine, Setting } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getPlanStats, type PlanStats } from '@/api/plan'
import { listTasks, type TaskItem } from '@/api/task'
import { useTimerStore } from '@/stores/timer'

const router = useRouter()
const timer = useTimerStore()
const { session: current } = storeToRefs(timer)
const stats = ref<PlanStats | null>(null)
const tasks = ref<TaskItem[]>([])

// 顶部/快捷操作卡的「正在计时」时长：订阅全局 store，由 MainLayout 持续推进
const liveElapsed = computed(() => fmt(timer.elapsedSec))

function fmt(s: number): string {
  s = Math.max(0, Math.floor(s))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  const mm = String(m).padStart(2, '0')
  const ss = String(sec).padStart(2, '0')
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`
}

const todayStr = () => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

async function loadAll() {
  try {
    const [s, t] = await Promise.all([
      getPlanStats('day'),
      listTasks({ date: todayStr() }),
    ])
    stats.value = s.data
    const list = t.data || []
    tasks.value = list
      .slice()
      .sort((a, b) => (a.start_time || '99:99').localeCompare(b.start_time || '99:99'))
      .slice(0, 8)
  } catch {
    /* ignore */
  }
}

// 行内「开始计时」→ 开启 task 模式计时（绑定计划时间段）+ 跳转。
// 如果已有 running session：弹窗确认是否结束旧任务，避免默默破坏用户进行中的学习。
async function startTask(t: TaskItem) {
  if (timer.running) {
    try {
      await ElMessageBox.confirm(
        `当前正在计时「${timer.session?.task?.content || timer.session?.note || '自由计时'}」，结束并开始新任务？`,
        '替换当前计时',
        { type: 'warning', confirmButtonText: '结束并开始', cancelButtonText: '取消' },
      )
    } catch {
      return  // 用户取消
    }
  }
  try { await timer.startTask(t) } catch { ElMessage.error('开始计时失败'); return }
  router.push('/timer')
}

const goUpload = () => router.push('/upload')
const goTimer = () => router.push('/timer')
const goStats = () => router.push('/stats')
const goSettings = () => router.push('/settings')
const goTasks = () => router.push('/tasks')

onMounted(async () => {
  await loadAll()
  // 全局 tick 由 MainLayout 驱动；本页不再重复 setInterval
})
</script>

<style scoped>
.dashboard { max-width: 1100px; margin: 0 auto; }
.ov-card { border-radius: 16px; }
.ov-label { font-size: 13px; color: var(--text-muted); }
.ov-value { font-size: 40px; font-weight: 800; color: var(--brand-700, #0F766E); line-height: 1.1; margin-top: 6px; }
.ov-value small { font-size: 16px; margin-left: 3px; }
.ov-value.sm { font-size: 22px; }
.ov-value.muted { color: var(--text-muted); }
.ov-sub { font-size: 12px; color: var(--text-muted); margin-top: 6px; }
.ov-prog { margin-top: 8px; }

.plan-card, .quick-card { border-radius: 16px; min-height: 280px; }
.card-head { display: flex; justify-content: space-between; align-items: center; font-weight: 600; margin-bottom: 12px; }
.empty { color: var(--text-muted); font-size: 13px; padding: 24px 0; text-align: center; }
.plan-list { list-style: none; margin: 0; padding: 0; }
.plan-item {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 8px; border-bottom: 1px solid var(--border);
}
.plan-item:last-child { border-bottom: none; }
.plan-item.done { opacity: .55; }
.plan-item.cancelled { opacity: .4; text-decoration: line-through; }
.p-time { font-variant-numeric: tabular-nums; font-weight: 600; color: var(--text-secondary); width: 64px; }
.p-subj { font-weight: 600; color: var(--text-strong); width: 90px; }
.p-content { flex: 1; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.quick-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.quick-btn { height: 64px; display: flex; flex-direction: column; gap: 4px; font-size: 13px; }
.running-tip { margin-top: 16px; }
</style>

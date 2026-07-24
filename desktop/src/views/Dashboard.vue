<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value">{{ stats.total }}</div>
            <div class="stat-label">今日任务</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value" :style="{ color: '#67c23a' }">{{ stats.completion_rate }}%</div>
            <div class="stat-label">完成率</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value" :style="{ color: '#409eff' }">{{ studyHours }}h</div>
            <div class="stat-label">今日学习</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value" :style="{ color: '#e6a23c' }">{{ streakDays }}天</div>
            <div class="stat-label">连续学习</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="16">
        <el-card>
          <template #header>
            <span>今日任务</span>
          </template>
          <div v-if="taskStore.tasks.length === 0" class="empty-state">
            <el-empty description="今天还没有学习任务" />
          </div>
          <el-timeline v-else>
            <el-timeline-item
              v-for="task in taskStore.tasks"
              :key="task.id"
              :timestamp="task.start_time || task.date"
              :color="task.status === 'done' ? '#67c23a' : task.status === 'cancelled' ? '#909399' : '#409eff'"
            >
              <div class="task-item">
                <el-tag :type="subjectTagType(task.subject)" size="small">{{ task.subject }}</el-tag>
                <span :class="{ 'task-done': task.status === 'done' }">{{ task.content }}</span>
                <span class="task-time">{{ task.start_time }}-{{ task.end_time }}</span>
              </div>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>快捷操作</span>
          </template>
          <div class="quick-actions">
            <el-button type="primary" class="action-btn" @click="$router.push('/home/tasks')">
              管理任务
            </el-button>
            <el-button type="success" class="action-btn" @click="$router.push('/home/timer')">
              开始学习
            </el-button>
            <el-button type="warning" class="action-btn" @click="$router.push('/home/ai')">
              AI 助手
            </el-button>
            <el-button type="info" class="action-btn" @click="$router.push('/home/import')">
              导入计划
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useTaskStore } from '@/stores/task'
import { taskApi, recordApi } from '@/api'

const taskStore = useTaskStore()
const stats = ref({ total: 0, done: 0, completion_rate: 0 })
const studyHours = ref(0)
const streakDays = ref(0)

function subjectTagType(subject: string) {
  const map: Record<string, string> = {
    '数学': 'danger',
    '英语': 'warning',
    '政治': 'success',
    '408': 'primary',
  }
  return map[subject] || 'info'
}

onMounted(async () => {
  try {
    await taskStore.fetchTasks()
    const statsRes: any = await taskApi.dailyStats()
    stats.value = statsRes.data

    const weeklyRes: any = await recordApi.weeklyStats()
    studyHours.value = weeklyRes.data.total_hours
    streakDays.value = weeklyRes.data.total_days
  } catch (err) {
    console.error('加载数据失败:', err)
  }
})
</script>

<style scoped>
.stat-card {
  text-align: center;
  padding: 12px 0;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-done {
  text-decoration: line-through;
  color: #909399;
}

.task-time {
  margin-left: auto;
  color: #909399;
  font-size: 12px;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.action-btn {
  width: 100%;
}

.empty-state {
  padding: 20px 0;
}
</style>
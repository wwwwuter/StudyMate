<template>
  <div class="tasks-page">
    <div class="page-header">
      <el-date-picker
        v-model="currentDate"
        type="date"
        placeholder="选择日期"
        value-format="YYYY-MM-DD"
        @change="handleDateChange"
      />
      <el-button type="primary" @click="showCreateDialog = true">新建任务</el-button>
    </div>

    <el-table :data="taskStore.tasks" stripe style="width: 100%">
      <el-table-column prop="date" label="日期" width="120" />
      <el-table-column prop="subject" label="科目" width="100">
        <template #default="{ row }">
          <el-tag :type="subjectTagType(row.subject)" size="small">{{ row.subject }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="content" label="内容" min-width="200" />
      <el-table-column prop="start_time" label="开始" width="80" />
      <el-table-column prop="end_time" label="结束" width="80" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">
            {{ statusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'pending'"
            size="small"
            type="success"
            @click="handleComplete(row)"
          >
            完成
          </el-button>
          <el-button
            v-if="row.status === 'pending'"
            size="small"
            @click="handleDelete(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建任务对话框 -->
    <el-dialog v-model="showCreateDialog" title="新建任务" width="500px">
      <el-form :model="newTask" label-width="80px">
        <el-form-item label="日期">
          <el-date-picker v-model="newTask.date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="科目">
          <el-select v-model="newTask.subject">
            <el-option label="数学" value="数学" />
            <el-option label="英语" value="英语" />
            <el-option label="政治" value="政治" />
            <el-option label="408" value="408" />
          </el-select>
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="newTask.content" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="开始时间">
          <el-time-picker v-model="newTask.start_time" format="HH:mm" value-format="HH:mm" />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-time-picker v-model="newTask.end_time" format="HH:mm" value-format="HH:mm" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useTaskStore } from '@/stores/task'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'

const taskStore = useTaskStore()
const currentDate = ref(dayjs().format('YYYY-MM-DD'))
const showCreateDialog = ref(false)
const newTask = ref({
  date: dayjs().format('YYYY-MM-DD'),
  subject: '数学',
  content: '',
  start_time: '',
  end_time: '',
})

function subjectTagType(subject: string) {
  const map: Record<string, string> = {
    '数学': 'danger', '英语': 'warning', '政治': 'success', '408': 'primary',
  }
  return map[subject] || 'info'
}

function statusTagType(status: string) {
  const map: Record<string, string> = {
    'pending': 'info', 'done': 'success', 'cancelled': 'danger',
  }
  return map[status] || 'info'
}

function statusText(status: string) {
  const map: Record<string, string> = {
    'pending': '待完成', 'done': '已完成', 'cancelled': '已取消',
  }
  return map[status] || status
}

function handleDateChange(date: string) {
  taskStore.setCurrentDate(date)
  taskStore.fetchTasks(date)
}

async function handleComplete(row: any) {
  try {
    await taskStore.updateTaskStatus(row.id, 'done')
    ElMessage.success('任务已完成')
  } catch {
    ElMessage.error('操作失败')
  }
}

async function handleDelete(row: any) {
  try {
    ElMessageBox.confirm('确定要删除此任务吗？', '提示').then(async () => {
      await taskStore.deleteTask(row.id)
      ElMessage.success('已删除')
    })
  } catch {
    // 取消操作
  }
}

async function handleCreate() {
  if (!newTask.value.content) {
    ElMessage.warning('请输入任务内容')
    return
  }
  try {
    await taskStore.createTask(newTask.value)
    showCreateDialog.value = false
    newTask.value.content = ''
    ElMessage.success('创建成功')
  } catch {
    ElMessage.error('创建失败')
  }
}

onMounted(() => {
  taskStore.fetchTasks()
})
</script>

<style scoped>
.tasks-page {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
</style>
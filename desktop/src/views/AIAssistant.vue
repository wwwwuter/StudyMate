<template>
  <div class="ai-page">
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card class="chat-card">
          <template #header>
            <span>AI 学习助手</span>
          </template>
          <div class="chat-messages" ref="chatRef">
            <div v-for="(msg, idx) in messages" :key="idx" :class="['msg', msg.role]">
              <div class="msg-content">{{ msg.content }}</div>
            </div>
            <div v-if="loading" class="msg assistant">
              <div class="msg-content">思考中...</div>
            </div>
          </div>
          <div class="chat-input">
            <el-input
              v-model="input"
              type="textarea"
              :rows="2"
              placeholder="输入你的学习问题..."
              @keydown.enter.prevent="sendMessage"
            />
            <el-button type="primary" :loading="loading" @click="sendMessage" style="margin-top: 8px">
              发送
            </el-button>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>快捷功能</span>
          </template>
          <div class="quick-actions">
            <el-button type="primary" class="action-btn" :loading="summaryLoading" @click="getDailySummary">
              今日学习总结
            </el-button>
            <el-button type="warning" class="action-btn" :loading="optimizeLoading" @click="getPlanOptimize">
              计划优化建议
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { aiApi } from '@/api'
import { ElMessage } from 'element-plus'

const messages = ref<{ role: string; content: string }[]>([
  { role: 'assistant', content: '你好！我是 StudyMate AI 学习助手。有什么可以帮你的吗？' },
])
const input = ref('')
const loading = ref(false)
const summaryLoading = ref(false)
const optimizeLoading = ref(false)
const chatRef = ref<HTMLElement | null>(null)

async function sendMessage() {
  if (!input.value.trim() || loading.value) return

  const msg = input.value
  messages.value.push({ role: 'user', content: msg })
  input.value = ''
  loading.value = true

  try {
    const res: any = await aiApi.chat(msg)
    messages.value.push({ role: 'assistant', content: res.data.answer })
  } catch {
    messages.value.push({ role: 'assistant', content: '抱歉，AI 服务暂时不可用。请检查 DeepSeek API 配置。' })
  } finally {
    loading.value = false
  }

  await nextTick()
  chatRef.value?.scrollTo({ top: chatRef.value.scrollHeight, behavior: 'smooth' })
}

async function getDailySummary() {
  summaryLoading.value = true
  try {
    const res: any = await aiApi.dailySummary()
    messages.value.push({ role: 'assistant', content: '📊 每日总结：\n\n' + res.data.output_data })
  } catch {
    ElMessage.error('获取总结失败')
  } finally {
    summaryLoading.value = false
  }
}

async function getPlanOptimize() {
  optimizeLoading.value = true
  try {
    const res: any = await aiApi.planOptimize()
    messages.value.push({ role: 'assistant', content: '📈 计划优化建议：\n\n' + res.data.output_data })
  } catch {
    ElMessage.error('获取建议失败')
  } finally {
    optimizeLoading.value = false
  }
}
</script>

<style scoped>
.chat-card {
  height: calc(100vh - 140px);
  display: flex;
  flex-direction: column;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
}

.msg {
  margin-bottom: 16px;
  display: flex;
}

.msg.user {
  justify-content: flex-end;
}

.msg-content {
  max-width: 80%;
  padding: 10px 16px;
  border-radius: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.msg.user .msg-content {
  background: #409eff;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.msg.assistant .msg-content {
  background: #f0f2f5;
  color: #303133;
  border-bottom-left-radius: 4px;
}

.chat-input {
  padding-top: 12px;
  border-top: 1px solid #e4e7ed;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.action-btn {
  width: 100%;
}
</style>
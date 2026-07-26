<template>
  <div class="rag-view">
    <div class="rag-head">
      <div>
        <h3 class="rag-title">AI 知识库</h3>
        <p class="rag-sub">
          基于你上传到「资料库」的学习资料进行问答；资料越丰富，回答越精准。
        </p>
      </div>
      <div class="rag-actions">
        <el-tag v-if="status" :type="status.indexed ? 'success' : 'info'" size="small" round>
          {{ status.indexed ? `已索引 ${status.chunk_count} 段` : '尚未索引' }}
        </el-tag>
        <el-button :loading="rebuilding" size="small" @click="rebuild">
          <el-icon><Refresh /></el-icon> 重建索引
        </el-button>
      </div>
    </div>

    <div ref="chatBox" class="rag-chat">
      <el-empty
        v-if="messages.length === 0"
        description="向你的资料库提问吧，例如：特征值与特征向量怎么理解？"
      />
      <div
        v-for="(m, i) in messages"
        :key="i"
        class="msg"
        :class="m.role"
      >
        <div class="bubble">
          <template v-if="m.role === 'user'">
            {{ m.text }}
          </template>
          <template v-else>
            <div class="answer-text" style="white-space: pre-wrap">{{ m.text }}</div>
            <div v-if="m.source" class="source-tag">
              <el-tag size="small" :type="sourceType(m.source)">
                {{ sourceLabel(m.source) }}
              </el-tag>
            </div>
            <div v-if="m.sources && m.sources.length" class="sources">
              <div
                v-for="(s, k) in m.sources"
                :key="k"
                class="source-card"
              >
                <div class="source-title">
                  <el-icon><Document /></el-icon>
                  <span>{{ s.title }}</span>
                  <span class="source-score">相关度 {{ (s.score * 100).toFixed(0) }}%</span>
                </div>
                <div class="source-snippet">{{ s.snippet }}</div>
              </div>
            </div>
          </template>
        </div>
      </div>

      <div v-if="loading" class="msg assistant">
        <div class="bubble loading">
          <span class="dot" /> <span class="dot" /> <span class="dot" /> 思考中…
        </div>
      </div>
    </div>

    <div class="rag-input">
      <el-input
        v-model="question"
        type="textarea"
        :rows="2"
        resize="none"
        placeholder="输入你的问题，回车发送（Shift+Enter 换行）"
        :disabled="loading"
        @keydown.enter.exact.prevent="send"
      />
      <el-button type="primary" :loading="loading" @click="send">
        <el-icon><Promotion /></el-icon> 发送
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Document, Promotion } from '@element-plus/icons-vue'
import { ragQuery, ragIndex, ragStatus } from '@/api/rag'
import type { RagStatus, RagSource } from '@/api/rag'

interface Message {
  role: 'user' | 'assistant'
  text: string
  source?: 'ai' | 'retrieval' | 'empty'
  sources?: RagSource[]
}

const question = ref('')
const loading = ref(false)
const rebuilding = ref(false)
const messages = ref<Message[]>([])
const status = ref<RagStatus | null>(null)
const chatBox = ref<HTMLElement | null>(null)

function sourceType(s: string): 'success' | 'warning' | 'info' {
  if (s === 'ai') return 'success'
  if (s === 'retrieval') return 'warning'
  return 'info'
}
function sourceLabel(s: string): string {
  if (s === 'ai') return 'DeepSeek 生成'
  if (s === 'retrieval') return '仅检索结果（未连 AI）'
  return '无相关资料'
}

async function loadStatus() {
  try {
    status.value = await ragStatus()
  } catch {
    /* 忽略 */
  }
}

async function send() {
  const q = question.value.trim()
  if (!q || loading.value) return
  messages.value.push({ role: 'user', text: q })
  question.value = ''
  loading.value = true
  await scrollDown()
  try {
    const data = await ragQuery(q)
    messages.value.push({
      role: 'assistant',
      text: data.answer,
      source: data.source,
      sources: data.sources,
    })
    loadStatus()
  } catch (e: any) {
    ElMessage.error(e?.message || '问答失败')
    messages.value.push({ role: 'assistant', text: '抱歉，本次问答出错，请稍后重试。' })
  } finally {
    loading.value = false
    await scrollDown()
  }
}

async function rebuild() {
  rebuilding.value = true
  try {
    await ragIndex()
    ElMessage.success('资料索引已重建')
    await loadStatus()
  } catch (e: any) {
    ElMessage.error(e?.message || '重建索引失败')
  } finally {
    rebuilding.value = false
  }
}

async function scrollDown() {
  await nextTick()
  if (chatBox.value) {
    chatBox.value.scrollTop = chatBox.value.scrollHeight
  }
}

onMounted(loadStatus)
</script>

<style scoped>
.rag-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 16px;
  overflow: hidden;
}
.rag-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}
.rag-title { margin: 0; font-size: 17px; color: var(--text-strong); font-weight: 700; }
.rag-sub { margin: 4px 0 0; font-size: 12px; color: var(--text-muted); }
.rag-actions { display: flex; align-items: center; gap: 10px; }

.rag-chat {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.msg { display: flex; }
.msg.user { justify-content: flex-end; }
.msg.assistant { justify-content: flex-start; }
.bubble {
  max-width: 78%;
  padding: 12px 14px;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
.msg.user .bubble {
  background: linear-gradient(135deg, #14B8A6, #0F766E);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.msg.assistant .bubble {
  background: var(--bg-page);
  color: var(--text-strong);
  border: 1px solid var(--border);
  border-bottom-left-radius: 4px;
}
.source-tag { margin-top: 8px; }
.sources { margin-top: 10px; display: flex; flex-direction: column; gap: 8px; }
.source-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 8px 10px;
}
.source-title {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; font-weight: 600; color: var(--text-strong);
}
.source-score { margin-left: auto; font-size: 11px; color: var(--text-muted); font-weight: 400; }
.source-snippet {
  margin-top: 4px; font-size: 12px; color: var(--text-muted);
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden;
}
.loading { color: var(--text-muted); }
.dot {
  display: inline-block; width: 6px; height: 6px; margin: 0 2px;
  border-radius: 50%; background: var(--text-muted);
  animation: blink 1.2s infinite both;
}
.dot:nth-child(2) { animation-delay: .2s; }
.dot:nth-child(3) { animation-delay: .4s; }
@keyframes blink { 0%, 80%, 100% { opacity: .2; } 40% { opacity: 1; } }

.rag-input {
  display: flex;
  gap: 10px;
  padding: 14px 16px;
  border-top: 1px solid var(--border);
  align-items: flex-end;
}
.rag-input .el-button { flex-shrink: 0; }
</style>

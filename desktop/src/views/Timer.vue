<template>
  <div class="timer-page">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>番茄钟</span>
          </template>
          <div class="timer-mode">
            <div class="timer-display">{{ formatTime(pomodoroTime) }}</div>
            <div class="timer-status">{{ pomodoroPhase === 'focus' ? '学习中' : '休息中' }}</div>
            <div class="timer-actions">
              <el-button
                v-if="!pomodoroRunning"
                type="primary"
                @click="startPomodoro"
              >
                开始
              </el-button>
              <el-button v-else type="danger" @click="stopPomodoro">
                暂停
              </el-button>
              <el-button @click="resetPomodoro">重置</el-button>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card>
          <template #header>
            <span>任务倒计时</span>
          </template>
          <div class="timer-mode">
            <div class="timer-display">{{ formatTime(countdownTime) }}</div>
            <div class="timer-status">绑定任务计时</div>
            <div class="timer-actions">
              <el-button
                v-if="!countdownRunning"
                type="primary"
                @click="startCountdown"
              >
                开始
              </el-button>
              <el-button v-else type="danger" @click="stopCountdown">
                暂停
              </el-button>
              <el-button @click="resetCountdown">重置</el-button>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card>
          <template #header>
            <span>正向计时</span>
          </template>
          <div class="timer-mode">
            <div class="timer-display">{{ formatTime(focusTime) }}</div>
            <div class="timer-status">{{ focusRunning ? '计时中' : '已停止' }}</div>
            <div class="timer-actions">
              <el-button
                v-if="!focusRunning"
                type="primary"
                @click="startFocus"
              >
                开始
              </el-button>
              <el-button v-else type="danger" @click="stopFocus">
                停止
              </el-button>
              <el-button @click="resetFocus">重置</el-button>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { recordApi } from '@/api'

// 番茄钟
const POMODORO_FOCUS = 25 * 60
const POMODORO_BREAK = 5 * 60
const pomodoroTime = ref(POMODORO_FOCUS)
const pomodoroRunning = ref(false)
const pomodoroPhase = ref<'focus' | 'break'>('focus')
let pomodoroTimer: number | null = null
let pomodoroRecordId: number | null = null

// 任务倒计时（默认2小时）
const TOTAL_COUNTDOWN = 2 * 3600
const countdownTime = ref(TOTAL_COUNTDOWN)
const countdownRunning = ref(false)
let countdownTimer: number | null = null
let countdownRecordId: number | null = null

// 正向计时
const focusTime = ref(0)
const focusRunning = ref(false)
let focusTimer: number | null = null
let focusRecordId: number | null = null

function formatTime(seconds: number) {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  return `${pad(h)}:${pad(m)}:${pad(s)}`
}

function pad(n: number) {
  return n.toString().padStart(2, '0')
}

// 番茄钟
async function startPomodoro() {
  pomodoroRunning.value = true
  try {
    const res: any = await recordApi.startRecord({ record_type: 'pomodoro' })
    pomodoroRecordId = res.data.id
  } catch {
    console.error('记录启动失败')
  }
  pomodoroTimer = window.setInterval(() => {
    if (pomodoroTime.value > 0) {
      pomodoroTime.value--
    } else {
      if (pomodoroPhase.value === 'focus') {
        pomodoroPhase.value = 'break'
        pomodoroTime.value = POMODORO_BREAK
        ElMessage.info('学习时间到！开始休息')
      } else {
        pomodoroPhase.value = 'focus'
        pomodoroTime.value = POMODORO_FOCUS
        ElMessage.info('休息结束！开始学习')
      }
    }
  }, 1000)
}

function stopPomodoro() {
  pomodoroRunning.value = false
  if (pomodoroTimer) {
    clearInterval(pomodoroTimer)
    pomodoroTimer = null
  }
  if (pomodoroRecordId) {
    recordApi.stopRecord(pomodoroRecordId)
    pomodoroRecordId = null
  }
}

function resetPomodoro() {
  stopPomodoro()
  pomodoroPhase.value = 'focus'
  pomodoroTime.value = POMODORO_FOCUS
}

// 任务倒计时
function startCountdown() {
  countdownRunning.value = true
  countdownTimer = window.setInterval(() => {
    if (countdownTime.value > 0) {
      countdownTime.value--
    } else {
      stopCountdown()
      ElMessage.success('倒计时结束！')
    }
  }, 1000)
}

function stopCountdown() {
  countdownRunning.value = false
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
}

function resetCountdown() {
  stopCountdown()
  countdownTime.value = TOTAL_COUNTDOWN
}

// 正向计时
async function startFocus() {
  focusRunning.value = true
  try {
    const res: any = await recordApi.startRecord({ record_type: 'focus' })
    focusRecordId = res.data.id
  } catch {
    console.error('记录启动失败')
  }
  focusTimer = window.setInterval(() => {
    focusTime.value++
  }, 1000)
}

async function stopFocus() {
  focusRunning.value = false
  if (focusTimer) {
    clearInterval(focusTimer)
    focusTimer = null
  }
  if (focusRecordId) {
    try {
      await recordApi.stopRecord(focusRecordId)
      focusRecordId = null
    } catch {
      console.error('记录停止失败')
    }
  }
}

function resetFocus() {
  stopFocus()
  focusTime.value = 0
}

onUnmounted(() => {
  stopPomodoro()
  stopCountdown()
  stopFocus()
})
</script>

<style scoped>
.timer-mode {
  text-align: center;
  padding: 20px 0;
}

.timer-display {
  font-size: 48px;
  font-weight: 700;
  font-family: 'Courier New', monospace;
  color: #303133;
  letter-spacing: 4px;
}

.timer-status {
  font-size: 16px;
  color: #909399;
  margin: 12px 0 20px;
}

.timer-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}
</style>
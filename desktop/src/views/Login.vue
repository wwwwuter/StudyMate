<template>
  <div class="login-container">
    <div class="login-card">
      <div class="logo">
        <h1>StudyMate</h1>
        <p class="subtitle">AI 智能考研学习助手</p>
      </div>
      <div class="login-form">
        <el-button type="primary" size="large" :loading="loading" class="login-btn" @click="handleLogin">
          <el-icon style="margin-right: 8px"><ChatDotRound /></el-icon>
          微信扫码登录
        </el-button>
        <p class="hint">支持 11408 考研学习计划管理</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)

async function handleLogin() {
  loading.value = true
  try {
    // 开发环境使用模拟 code
    const mockCode = 'mock_code_' + Date.now()
    await userStore.login(mockCode)
    ElMessage.success('登录成功')
    router.push('/home')
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  background: #fff;
  border-radius: 16px;
  padding: 48px 40px;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  min-width: 380px;
}

.logo h1 {
  font-size: 32px;
  color: #303133;
  margin-bottom: 8px;
}

.subtitle {
  color: #909399;
  font-size: 14px;
  margin-bottom: 32px;
}

.login-btn {
  width: 100%;
  font-size: 16px;
  padding: 12px 24px;
  border-radius: 8px;
}

.hint {
  margin-top: 16px;
  color: #c0c4cc;
  font-size: 12px;
}
</style>
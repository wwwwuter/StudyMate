<template>
  <div class="auth-wrap">
    <el-card class="auth-card" shadow="never">
      <h2 class="title">StudyMate</h2>
      <p class="subtitle">{{ needsSetup ? '首次使用，设置你的本地账号' : '登录你的本地账号' }}</p>

      <el-form @submit.prevent="submit" label-position="top">
        <el-form-item label="用户名">
          <el-input v-model="username" placeholder="输入用户名" :disabled="loading" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="password"
            type="password"
            show-password
            placeholder="至少 6 位"
            :disabled="loading"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button
          type="primary"
          class="submit-btn"
          :loading="loading"
          @click="submit"
        >
          {{ submitText }}
        </el-button>
      </el-form>

      <p v-if="error" class="error">{{ error }}</p>

      <!-- 网站多用户：非首次初始化时，登录/注册可切换 -->
      <div v-if="!needsSetup" class="switch">
        <el-link type="primary" @click="mode = mode === 'login' ? 'register' : 'login'">
          {{ mode === 'login' ? '没有账号？去注册' : '已有账号？去登录' }}
        </el-link>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const user = useUserStore()
const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
// 认证模式：setup=首次初始化, login=登录, register=注册
const mode = ref<'login' | 'register'>('login')

const needsSetup = computed(() => user.needsSetup)
const submitText = computed(() => {
  if (needsSetup.value) return '初始化账号'
  return mode.value === 'register' ? '注册' : '登录'
})

onMounted(() => {
  user.bootstrap()
})

async function submit() {
  error.value = ''
  if (!username.value.trim() || !password.value) {
    error.value = '请输入用户名和密码'
    return
  }
  if (password.value.length < 6) {
    error.value = '密码至少 6 位'
    return
  }
  loading.value = true
  try {
    if (needsSetup.value) {
      await user.setup(username.value.trim(), password.value)
    } else if (mode.value === 'register') {
      await user.register(username.value.trim(), password.value)
    } else {
      await user.login(username.value.trim(), password.value)
    }
    // 登录/注册/初始化成功后跳转到主页
    router.push('/')
  } catch (e: any) {
    error.value = e?.message || '操作失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: var(--el-bg-color-page, #f5f6f8);
}
.auth-card {
  width: 340px;
  padding: 12px 8px;
}
.title {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  text-align: center;
}
.subtitle {
  margin: 6px 0 20px;
  text-align: center;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.submit-btn {
  width: 100%;
  margin-top: 8px;
}
.switch {
  text-align: center;
  margin-top: 14px;
}
.error {
  color: var(--el-color-danger);
  font-size: 13px;
  text-align: center;
  margin-top: 12px;
}
</style>

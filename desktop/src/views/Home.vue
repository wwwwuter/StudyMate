<template>
  <el-container class="home-container">
    <el-aside width="220px" class="sidebar">
      <div class="sidebar-header">
        <h2>StudyMate</h2>
      </div>
      <el-menu
        :default-active="route.path"
        router
        class="sidebar-menu"
        background-color="#1d1e1f"
        text-color="#bfcbd9"
        active-text-color="#409eff"
      >
        <el-menu-item index="/home/dashboard">
          <el-icon><Odometer /></el-icon>
          <span>学习看板</span>
        </el-menu-item>
        <el-menu-item index="/home/tasks">
          <el-icon><List /></el-icon>
          <span>学习任务</span>
        </el-menu-item>
        <el-menu-item index="/home/timer">
          <el-icon><Timer /></el-icon>
          <span>学习计时</span>
        </el-menu-item>
        <el-menu-item index="/home/stats">
          <el-icon><DataAnalysis /></el-icon>
          <span>学习统计</span>
        </el-menu-item>
        <el-menu-item index="/home/ai">
          <el-icon><MagicStick /></el-icon>
          <span>AI 助手</span>
        </el-menu-item>
        <el-menu-item index="/home/import">
          <el-icon><Upload /></el-icon>
          <span>导入计划</span>
        </el-menu-item>
      </el-menu>
      <div class="sidebar-footer">
        <el-dropdown trigger="click" @command="handleCommand">
          <span class="user-info">
            <el-avatar :size="32" :src="userStore.user?.avatar" />
            <span class="username">{{ userStore.user?.nickname || '用户' }}</span>
          </span>
          <template #dropdown>
            <el-dropdown-item command="logout">退出登录</el-dropdown-item>
          </template>
        </el-dropdown>
      </div>
    </el-aside>
    <el-container>
      <el-header class="header">
        <el-breadcrumb>
          <el-breadcrumb-item :to="{ path: '/home/dashboard' }">首页</el-breadcrumb-item>
          <el-breadcrumb-item>{{ route.meta.title }}</el-breadcrumb-item>
        </el-breadcrumb>
      </el-header>
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

function handleCommand(command: string) {
  if (command === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗？', '提示').then(() => {
      userStore.logout()
      router.push('/login')
    })
  }
}
</script>

<style scoped>
.home-container {
  height: 100vh;
}

.sidebar {
  background-color: #1d1e1f;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 20px;
  text-align: center;
}

.sidebar-header h2 {
  color: #fff;
  font-size: 20px;
  font-weight: 600;
}

.sidebar-menu {
  flex: 1;
  border-right: none;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid #333;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #bfcbd9;
}

.username {
  font-size: 14px;
}

.header {
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  padding: 0 20px;
}

.main-content {
  background: #f5f7fa;
  padding: 20px;
  overflow-y: auto;
}
</style>
<template>
  <el-container class="app-shell">
    <!-- 侧边栏 -->
    <el-aside width="224px" class="app-aside">
      <div class="brand">
        <div class="brand-logo">
          <span class="brand-mark">S</span>
        </div>
        <div class="brand-text">
          <div class="brand-name">StudyMate</div>
          <div class="brand-sub">专注计时学习助手</div>
        </div>
      </div>

      <el-menu :default-active="activeMenu" class="app-menu" router>
        <el-menu-item index="/">
          <el-icon><HomeFilled /></el-icon>
          <span>首页</span>
        </el-menu-item>
        <el-menu-item index="/upload">
          <el-icon><Upload /></el-icon>
          <span>上传计划</span>
        </el-menu-item>
        <el-menu-item index="/tasks">
          <el-icon><List /></el-icon>
          <span>今日计划</span>
        </el-menu-item>
        <el-menu-item index="/timer">
          <el-icon><Timer /></el-icon>
          <span>计时</span>
        </el-menu-item>
        <el-menu-item index="/stats">
          <el-icon><DataLine /></el-icon>
          <span>学习记录</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>设置</span>
        </el-menu-item>
      </el-menu>

      <div class="aside-foot">
        <div class="ai-chip">
          <el-icon><MagicStick /></el-icon>
          <span>AI 计划识别已就绪</span>
        </div>
      </div>
    </el-aside>

    <!-- 主体 -->
    <el-container>
      <el-header class="app-header">
        <div class="header-title">
          <h2>{{ pageTitle }}</h2>
          <p class="header-date">{{ todayText }}</p>
        </div>

        <div class="header-actions">
          <el-badge :value="pendingCount" :hidden="pendingCount === 0" :max="99" class="bell">
            <el-button circle text @click="reminderVisible = true">
              <el-icon :size="18"><Bell /></el-icon>
            </el-button>
          </el-badge>
          <el-avatar :size="36" class="user-avatar">研</el-avatar>
          <div class="user-meta">
            <div class="user-name">考研同学</div>
            <div class="user-role">考研ing · 2027</div>
          </div>
        </div>
      </el-header>

      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>

    <ReminderSettings
      :visible="reminderVisible"
      @update:visible="reminderVisible = $event"
      @saved="refreshCount"
    />

    <!-- 前台运行时弹出的学习提醒 -->
    <ReminderPopup />
  </el-container>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import {
  List, Upload, Timer, Setting, HomeFilled, DataLine,
  MagicStick, Bell,
} from '@element-plus/icons-vue'
import ReminderSettings from '@/views/ReminderSettings.vue'
import ReminderPopup from '@/views/ReminderPopup.vue'
import { getPendingReminders } from '@/api/reminder'

const route = useRoute()

const titleMap: Record<string, string> = {
  '/': '首页',
  '/upload': '上传计划',
  '/tasks': '今日计划',
  '/timer': '计时',
  '/stats': '学习记录',
  '/settings': '设置',
}
const pageTitle = computed(() => titleMap[route.path] ?? 'StudyMate')
const activeMenu = computed(() => route.path)

const todayText = new Date().toLocaleDateString('zh-CN', {
  year: 'numeric', month: 'long', day: 'numeric', weekday: 'long',
})

// ---- 提醒：铃铛入口 + 待提醒数量徽标 ----
const reminderVisible = ref(false)
const pendingCount = ref(0)
let countTimer: number | undefined

async function refreshCount() {
  try {
    const res = await getPendingReminders()
    pendingCount.value = (res.data || []).length
  } catch {
    /* 忽略瞬时错误 */
  }
}

onMounted(() => {
  refreshCount()
  countTimer = window.setInterval(refreshCount, 20_000)
})
onBeforeUnmount(() => {
  if (countTimer !== undefined) {
    clearInterval(countTimer)
    countTimer = undefined
  }
})
</script>

<style scoped>
.app-shell { height: 100vh; }

/* 侧边栏 */
.app-aside {
  background: linear-gradient(180deg, #0F766E 0%, #0C5E58 100%);
  display: flex;
  flex-direction: column;
  padding: 18px 14px;
  color: #fff;
}
.brand { display: flex; align-items: center; gap: 12px; padding: 6px 8px 18px; }
.brand-logo {
  width: 40px; height: 40px; border-radius: 12px;
  background: rgba(255,255,255,.16);
  display: grid; place-items: center;
}
.brand-mark {
  font-size: 20px; font-weight: 800; color: #fff;
  font-family: var(--font-sans);
}
.brand-name { font-size: 17px; font-weight: 700; letter-spacing: .5px; }
.brand-sub { font-size: 11px; opacity: .75; }

.app-menu {
  flex: 1;
  background: transparent;
  border-right: none;
}
.app-menu :deep(.el-menu-item) {
  border-radius: 10px;
  margin: 4px 0;
  color: rgba(255,255,255,.82);
  height: 46px;
}
.app-menu :deep(.el-menu-item.is-active) {
  background: rgba(255,255,255,.16);
  color: #fff;
  border-right: none;
  font-weight: 600;
}
.app-menu :deep(.el-menu-item:not(.is-active):hover) {
  background: rgba(255,255,255,.10);
  color: #fff;
}
.app-menu :deep(.el-menu-item .el-icon) { color: inherit; }

.aside-foot { padding-top: 12px; }
.ai-chip {
  display: flex; align-items: center; gap: 8px;
  background: rgba(255,255,255,.12);
  border: 1px solid rgba(255,255,255,.18);
  border-radius: 999px;
  padding: 8px 14px; font-size: 13px;
}

/* 顶栏 */
.app-header {
  height: 68px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 24px;
  padding: 0 24px;
}
.header-title h2 { margin: 0; font-size: 18px; color: var(--text-strong); font-weight: 700; }
.header-date { margin: 0; font-size: 12px; color: var(--text-muted); }
.header-actions { display: flex; align-items: center; gap: 14px; margin-left: auto; }
.bell :deep(.el-button) { color: var(--text-secondary); }
.user-avatar { background: linear-gradient(135deg, #14B8A6, #0F766E); color: #fff; font-weight: 700; }
.user-meta { line-height: 1.2; }
.user-name { font-size: 13px; font-weight: 600; color: var(--text-strong); }
.user-role { font-size: 11px; color: var(--text-muted); }

/* 内容区 */
.app-main {
  background: var(--bg-page);
  padding: 24px;
  overflow-y: auto;
}
</style>

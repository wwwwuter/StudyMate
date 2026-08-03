<template>
  <el-container class="app-shell">
    <!-- 侧边栏（窄屏 <768px 折叠为 64px 图标栏，适配手机/小屏） -->
    <el-aside :width="isNarrow ? '64px' : '224px'" class="app-aside" :class="{ narrow: isNarrow }">
      <div class="brand">
        <div class="brand-logo">
          <span class="brand-mark">S</span>
        </div>
        <div v-if="!isNarrow" class="brand-text">
          <div class="brand-name">StudyMate</div>
          <div class="brand-sub">专注计时学习助手</div>
        </div>
      </div>

      <el-menu :default-active="activeMenu" class="app-menu" router :collapse="isNarrow" :collapse-transition="false">
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

      <div v-if="!isNarrow" class="aside-foot">
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
          <button v-if="timerRunning" class="timer-chip" @click="router.push('/timer')">
            <span class="chip-dot"></span>
            <span class="chip-label">{{ timerSummary?.label }}</span>
            <span class="chip-clock">{{ timerSummary?.clock }}</span>
          </button>
          <el-badge :value="pendingCount" :hidden="pendingCount === 0" :max="99" class="bell">
            <el-button circle text @click="reminderVisible = true">
              <el-icon :size="18"><Bell /></el-icon>
            </el-button>
          </el-badge>
          <el-dropdown trigger="click" @command="onUserCommand">
            <div class="user-box">
              <el-avatar :size="36" class="user-avatar">{{ avatarText }}</el-avatar>
              <div class="user-meta">
                <div class="user-name">{{ user.username || '未登录' }}</div>
                <div class="user-role">{{ user.isLoggedIn ? '已登录' : '点击登录' }}</div>
              </div>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout" :disabled="!user.isLoggedIn" divided>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>

    <ReminderSettings
      :visible="reminderVisible"
      @update:visible="reminderVisible = $event"
      @saved="reminder.refreshPending"
    />

    <!-- 前台运行时弹出的学习提醒 -->
    <ReminderPopup />

    <!-- 计时结束后的「是否完成任务」判定弹窗（全局） -->
    <CompleteTaskDialog />
  </el-container>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import {
  List, Upload, Timer, Setting, HomeFilled, DataLine,
  MagicStick, Bell,
} from '@element-plus/icons-vue'
import ReminderSettings from '@/views/ReminderSettings.vue'
import ReminderPopup from '@/views/ReminderPopup.vue'
import CompleteTaskDialog from '@/views/CompleteTaskDialog.vue'
import { useUserStore } from '@/stores/user'
import { useTimerStore } from '@/stores/timer'
import { useReminderStore } from '@/stores/reminder'

const route = useRoute()
const router = useRouter()
const user = useUserStore()
const timer = useTimerStore()
const reminder = useReminderStore()
const { summary: timerSummary, running: timerRunning } = storeToRefs(timer)
const { pendingCount } = storeToRefs(reminder)

// 头像取用户名首字符（未登录时兜底「研」）
const avatarText = computed(() => (user.username || '研').charAt(0).toUpperCase())

/** 顶栏用户下拉：目前仅「退出登录」一项；登出后回登录页。 */
function onUserCommand(cmd: string) {
  if (cmd === 'logout') {
    user.logout()
    router.push('/auth')
  }
}

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

// ---- 窄屏适配（<768px 侧边栏折叠为图标栏，适配手机/小屏平板）----
const isNarrow = ref(typeof window !== 'undefined' && window.innerWidth < 768)
function onResize() {
  isNarrow.value = typeof window !== 'undefined' && window.innerWidth < 768
}

// ---- 提醒：铃铛入口 + 待提醒数量徽标（全局 store，轮询刷新）----
const reminderVisible = ref(false)
let countTimer: number | undefined

onMounted(() => {
  window.addEventListener('resize', onResize)
  reminder.refreshPending()
  countTimer = window.setInterval(() => reminder.refreshPending(), 20_000)
  // Phase 6-4 修正：tick 由 MainLayout 驱动（永远挂载），保证跨页面计时推进
  timer.startTicking()
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  if (countTimer !== undefined) {
    clearInterval(countTimer)
    countTimer = undefined
  }
  timer.stopTicking()
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
.app-aside.narrow { padding: 18px 0; }
.app-aside.narrow .brand { justify-content: center; padding: 6px 0 18px; }
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
.timer-chip {
  display: inline-flex; align-items: center; gap: 8px;
  border: 1px solid var(--border-secondary, rgba(20, 184, 166, 0.35));
  background: var(--color-background-secondary, #F0FDFA);
  border-radius: 999px; padding: 6px 14px; cursor: pointer;
  font-size: 13px; color: var(--brand-700, #0F766E); transition: all .15s;
}
.timer-chip:hover { background: var(--color-background-info, #E6F1FB); }
.chip-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #10B981; box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.18);
  animation: chip-pulse 1.6s ease-in-out infinite;
}
@keyframes chip-pulse { 0%, 100% { opacity: 1; } 50% { opacity: .45; } }
.chip-label { max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500; }
.chip-clock { font-variant-numeric: tabular-nums; font-weight: 600; }
.bell :deep(.el-button) { color: var(--text-secondary); }
.user-box { display: flex; align-items: center; gap: 10px; cursor: pointer; padding: 4px 6px; border-radius: 8px; }
.user-box:hover { background: var(--el-fill-color-light); }
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

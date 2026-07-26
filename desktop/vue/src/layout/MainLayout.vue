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
          <div class="brand-sub">智能考研学习助手</div>
        </div>
      </div>

      <el-menu :default-active="activeMenu" class="app-menu" router>
        <el-menu-item index="/">
          <el-icon><Odometer /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/plan">
          <el-icon><Calendar /></el-icon>
          <span>学习计划</span>
        </el-menu-item>
        <el-menu-item index="/tasks">
          <el-icon><List /></el-icon>
          <span>任务</span>
        </el-menu-item>
        <el-menu-item index="/timer">
          <el-icon><Timer /></el-icon>
          <span>计时</span>
        </el-menu-item>
        <el-menu-item index="/materials">
          <el-icon><Files /></el-icon>
          <span>资料库</span>
        </el-menu-item>
        <el-menu-item index="/ai">
          <el-icon><ChatDotRound /></el-icon>
          <span>AI 助手</span>
        </el-menu-item>
        <el-menu-item index="/stats">
          <el-icon><DataLine /></el-icon>
          <span>数据统计</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>设置</span>
        </el-menu-item>
      </el-menu>

      <div class="aside-foot">
        <div class="ai-chip">
          <el-icon><MagicStick /></el-icon>
          <span>AI 已就绪</span>
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

        <div class="header-search">
          <el-input
            placeholder="搜索课程、资料、任务…"
            :prefix-icon="Search"
            clearable
          />
        </div>

        <div class="header-actions">
          <el-badge :value="3" class="bell">
            <el-button circle text><el-icon :size="18"><Bell /></el-icon></el-button>
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
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  Odometer, Calendar, List, ChatDotRound, DataLine, Setting,
  MagicStick, Bell, Search, Timer, Files,
} from '@element-plus/icons-vue'

const route = useRoute()

const titleMap: Record<string, string> = {
  '/': '仪表盘',
  '/plan': '学习计划',
  '/tasks': '任务',
  '/timer': '计时',
  '/materials': '资料库',
  '/ai': 'AI 助手',
  '/stats': '数据统计',
  '/settings': '设置',
}
const pageTitle = computed(() => titleMap[route.path] ?? 'StudyMate')
const activeMenu = computed(() => route.path)

const todayText = new Date().toLocaleDateString('zh-CN', {
  year: 'numeric', month: 'long', day: 'numeric', weekday: 'long',
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
.header-search { flex: 1; max-width: 420px; }
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

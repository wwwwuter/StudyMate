<template>
  <div class="coming-soon">
    <el-icon :size="48" class="cs-icon"><DocumentAdd /></el-icon>
    <h3>{{ title }}</h3>
    <p>该模块将在后续阶段实现。</p>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { DocumentAdd } from '@element-plus/icons-vue'

const route = useRoute()
const map: Record<string, string> = {
  '/plan': '学习计划',
  '/tasks': '任务',
  '/ai': 'AI 助手',
  '/stats': '数据统计',
  '/settings': '设置',
}
const title = map[route.path] ?? '模块'
</script>

<style scoped>
.coming-soon {
  height: 100%;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  color: var(--text-muted);
  gap: 8px;
}
.cs-icon { color: var(--brand-500); }
.coming-soon h3 { margin: 4px 0 0; color: var(--text-secondary); font-weight: 600; }
.coming-soon p { margin: 0; font-size: 13px; }
</style>

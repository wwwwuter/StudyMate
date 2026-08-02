<template>
  <div class="stat-view">
    <div class="stat-view-head">
      <h3 class="stat-view-title">学习统计</h3>
      <p class="stat-view-sub">围绕「计划 → 执行 → 反馈」的学习闭环，看清每天与长期的投入。</p>
    </div>

    <el-tabs v-model="tab" class="stat-tabs">
      <el-tab-pane label="今日" name="today" lazy>
        <TodayStat />
      </el-tab-pane>
      <el-tab-pane label="全部" name="all" lazy>
        <AllStat />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import TodayStat from './TodayStat.vue'
import AllStat from './AllStat.vue'

const tab = ref<'today' | 'all'>('today')
</script>

<style scoped>
.stat-view {
  max-width: 1140px;
  margin: 0 auto;
}
.stat-view-head {
  margin-bottom: 14px;
}
.stat-view-title {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  color: #1f2937;
}
.stat-view-sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: #8a94a6;
}
.stat-tabs {
  --el-color-primary: #0f766e;
}
.stat-tabs :deep(.el-tabs__header) {
  margin-bottom: 18px;
}
</style>

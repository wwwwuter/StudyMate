<template>
  <div class="stat-card">
    <div class="stat-label">{{ label }}</div>
    <div class="stat-value">{{ value }}</div>
    <div v-if="hint" class="stat-hint">{{ hint }}</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  label: string
  value: string
  hint?: string
}>()
</script>

<style scoped>
.stat-card {
  background: #fff;
  border: 1px solid #eef1f4;
  border-radius: 14px;
  padding: 16px 18px;
  box-shadow: 0 2px 10px rgba(15, 118, 110, 0.05);
  min-height: 92px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.stat-label {
  font-size: 13px;
  color: #8a94a6;
  margin-bottom: 8px;
}
.stat-value {
  font-size: 24px;
  font-weight: 800;
  color: #0f766e;
  line-height: 1.1;
  word-break: break-all;
}
.stat-hint {
  margin-top: 6px;
  font-size: 12px;
  color: #aab2bf;
}
</style>

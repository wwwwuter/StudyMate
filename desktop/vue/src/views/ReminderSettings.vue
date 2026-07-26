<template>
  <el-dialog
    title="提醒设置"
    :model-value="visible"
    width="440px"
    @update:model-value="emit('update:visible', $event)"
  >
    <el-form label-width="104px">
      <el-form-item label="任务开始前提醒">
        <el-switch v-model="form.enabled" />
      </el-form-item>
      <el-form-item label="提前提醒">
        <el-input-number v-model="form.lead_minutes" :min="0" :max="600" :step="5" />
        <span class="suffix">分钟</span>
      </el-form-item>
      <el-alert type="info" :closable="false" show-icon>
        <template #title>说明</template>
        到点为「即将开始」的任务弹出系统通知。后端由 APScheduler 周期扫描生成提醒，
        桌面端以 Electron 系统通知呈现（窗口最小化也会弹出）。
      </el-alert>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getReminderSettings, saveReminderSettings } from '@/api/reminder'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{
  (e: 'update:visible', v: boolean): void
  (e: 'saved'): void
}>()

const form = ref({ enabled: true, lead_minutes: 10 })
const saving = ref(false)

watch(
  () => props.visible,
  (v) => {
    if (v) load()
  },
)

async function load() {
  try {
    const res = await getReminderSettings()
    form.value = { enabled: res.data.enabled, lead_minutes: res.data.lead_minutes }
  } catch {
    /* 忽略，使用默认值 */
  }
}

async function save() {
  saving.value = true
  try {
    await saveReminderSettings({
      enabled: form.value.enabled,
      lead_minutes: form.value.lead_minutes,
    })
    ElMessage.success('已保存')
    emit('saved')
    emit('update:visible', false)
  } catch (e) {
    ElMessage.error((e as Error).message || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.suffix {
  margin-left: 8px;
  color: var(--text-muted);
  font-size: 13px;
}
</style>

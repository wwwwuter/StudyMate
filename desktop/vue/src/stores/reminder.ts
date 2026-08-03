import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getBootstrap } from '@/api/bootstrap'
import { getPendingReminders } from '@/api/reminder'

/** 全局提醒状态（Phase 6-3）：enabled 来自 bootstrap，pending 数由轮询刷新。 */
export const useReminderStore = defineStore('reminder', () => {
  const enabled = ref(true)
  const pendingCount = ref(0)
  const hydrated = ref(false)

  async function hydrate() {
    try {
      const data = await getBootstrap()
      enabled.value = data.reminder.enabled
    } catch {
      /* 忽略瞬时错误 */
    }
    hydrated.value = true
  }

  async function refreshPending() {
    try {
      const res = await getPendingReminders()
      pendingCount.value = (res.data || []).length
    } catch {
      /* 忽略瞬时错误 */
    }
  }

  return { enabled, pendingCount, hydrated, hydrate, refreshPending }
})

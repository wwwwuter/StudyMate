import request from '@/api/request'

export interface ReminderItem {
  id: number
  task_id: number | null
  type: string
  subject: string
  content: string
  fire_at: string
  lead_minutes: number
  delivered: boolean
}

export interface ReminderSettings {
  enabled: boolean
  lead_minutes: number
}

export const getPendingReminders = () =>
  request
    .get('/reminders/pending')
    .then((r) => r.data as { code: number; data: ReminderItem[] })

export const ackReminders = (ids: number[]) =>
  request.post('/reminders/ack', { ids }).then((r) => r.data)

export const getReminderSettings = () =>
  request
    .get('/reminders/settings')
    .then((r) => r.data as { code: number; data: ReminderSettings })

export const saveReminderSettings = (payload: Partial<ReminderSettings>) =>
  request.post('/reminders/settings', payload).then((r) => r.data)

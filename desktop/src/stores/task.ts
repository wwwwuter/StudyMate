import { defineStore } from 'pinia'
import { ref } from 'vue'
import { taskApi, recordApi } from '@/api'
import dayjs from 'dayjs'

interface StudyTask {
  id: number
  user_id: number
  date: string
  subject: string
  content: string
  start_time: string | null
  end_time: string | null
  status: string
  plan_source: string
  create_time: string
}

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<StudyTask[]>([])
  const currentDate = ref(dayjs().format('YYYY-MM-DD'))

  async function fetchTasks(date?: string) {
    const res: any = await taskApi.getTasks(date || currentDate.value)
    tasks.value = res.data
  }

  async function createTask(data: any) {
    await taskApi.createTask(data)
    await fetchTasks()
  }

  async function updateTaskStatus(id: number, status: string) {
    await taskApi.updateTask(id, { status })
    await fetchTasks()
  }

  async function deleteTask(id: number) {
    await taskApi.deleteTask(id)
    await fetchTasks()
  }

  function setCurrentDate(date: string) {
    currentDate.value = date
  }

  return {
    tasks,
    currentDate,
    fetchTasks,
    createTask,
    updateTaskStatus,
    deleteTask,
    setCurrentDate,
  }
})
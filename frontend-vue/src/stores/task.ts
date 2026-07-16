import { ref } from 'vue'
import { defineStore } from 'pinia'
import { taskService, type Task } from '../services/api'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<Task[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(10)
  const isLoading = ref(false)

  async function fetchTasks(pageNum = page.value) {
    isLoading.value = true
    try {
      let data = await taskService.getTasks(pageNum, pageSize.value)
      let resolvedPage = pageNum

      if (data.total > 0 && data.tasks.length === 0 && pageNum > 1) {
        resolvedPage = Math.max(1, Math.ceil(data.total / pageSize.value))
        data = await taskService.getTasks(resolvedPage, pageSize.value)
      }

      tasks.value = data.tasks || []
      total.value = data.total
      page.value = resolvedPage
    } finally {
      isLoading.value = false
    }
  }

  async function deleteTask(taskId: number) {
    await taskService.deleteTask(taskId)
    await fetchTasks(page.value)
  }

  async function stopTask(taskId: number) {
    await taskService.stopTask(taskId)
    await fetchTasks(page.value)
  }

  async function clarifyTask(taskId: number, input: string) {
    await taskService.clarifyTask(taskId, input)
    await fetchTasks(page.value)
  }

  return {
    tasks,
    total,
    page,
    pageSize,
    isLoading,
    fetchTasks,
    deleteTask,
    stopTask,
    clarifyTask,
  }
})

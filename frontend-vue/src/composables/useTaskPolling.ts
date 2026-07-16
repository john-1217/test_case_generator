import { onMounted, onUnmounted } from 'vue'
import { useTaskStore } from '../stores/task'

export function useTaskPolling(intervalMs = 5000) {
  const taskStore = useTaskStore()
  let timer: ReturnType<typeof setInterval> | null = null

  function start() {
    stop()
    timer = setInterval(() => {
      taskStore.fetchTasks().catch(console.error)
    }, intervalMs)
  }

  function stop() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  onMounted(start)
  onUnmounted(stop)

  return { start, stop }
}

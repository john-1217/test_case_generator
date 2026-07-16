<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import TaskTable from '../components/task/TaskTable.vue'
import ClarificationDialog from '../components/task/ClarificationDialog.vue'
import ProgressDialog from '../components/task/ProgressDialog.vue'
import SummaryDialog from '../components/task/SummaryDialog.vue'
import { useTaskPolling } from '../composables/useTaskPolling'
import { useTaskStore } from '../stores/task'
import { taskService, type Task } from '../services/api'

const taskStore = useTaskStore()
useTaskPolling()

const clarifyOpen = ref(false)
const progressOpen = ref(false)
const summaryOpen = ref(false)
const selectedTaskId = ref<number | null>(null)

const selectedTask = computed(() => taskStore.tasks.find((task) => task.task_id === selectedTaskId.value) || null)

onMounted(async () => {
  try {
    await taskStore.fetchTasks()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '加载任务列表失败')
  }
})

function openClarify(task: Task) {
  selectedTaskId.value = task.task_id
  clarifyOpen.value = true
}

function openProgress(task: Task) {
  selectedTaskId.value = task.task_id
  progressOpen.value = true
}

async function openSummary(task: Task) {
  selectedTaskId.value = task.task_id
  try {
    if (!task.summary_content) {
      const result = await taskService.getSummary(task.task_id)
      task.summary_content = result.summary
    }
    summaryOpen.value = true
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '获取总结失败')
  }
}
</script>

<template>
  <section class="tasks-view">
    <div class="page-header">
      <div>
        <h2>任务列表</h2>
        <p>共 {{ taskStore.total }} 个任务</p>
      </div>
      <el-button :loading="taskStore.isLoading" @click="taskStore.fetchTasks()">刷新</el-button>
    </div>

    <TaskTable
      :tasks="taskStore.tasks"
      :is-loading="taskStore.isLoading"
      @refresh="taskStore.fetchTasks()"
      @clarify="openClarify"
      @progress="openProgress"
      @summary="openSummary"
    />

    <div v-if="taskStore.total > taskStore.pageSize" class="pagination">
      <el-pagination
        background
        layout="prev, pager, next, total"
        :current-page="taskStore.page"
        :page-size="taskStore.pageSize"
        :total="taskStore.total"
        @current-change="(page: number) => taskStore.fetchTasks(page)"
      />
    </div>

    <ClarificationDialog v-model="clarifyOpen" :task="selectedTask" @submitted="taskStore.fetchTasks()" />
    <ProgressDialog v-model="progressOpen" :task="selectedTask" />
    <SummaryDialog v-model="summaryOpen" :task="selectedTask" />
  </section>
</template>

<style scoped>
.tasks-view { display: flex; flex-direction: column; gap: 18px; }
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px;
  border-radius: var(--radius-lg);
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  backdrop-filter: var(--glass-backdrop);
}
h2 { margin: 0; font-size: 24px; }
p { margin: 6px 0 0; color: var(--color-text-secondary); }
.pagination { display: flex; justify-content: center; padding: 10px 0 24px; }
</style>

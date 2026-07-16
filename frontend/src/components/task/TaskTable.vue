<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import StatusBadge from '../ui/StatusBadge.vue'
import { TaskStatus, type Task, taskService } from '../../services/api'

const props = defineProps<{
  tasks: Task[]
  isLoading: boolean
}>()

const emit = defineEmits<{
  refresh: []
  clarify: [task: Task]
  progress: [task: Task]
  summary: [task: Task]
}>()

const downloadingTaskId = ref<number | null>(null)
const stoppingTaskId = ref<number | null>(null)
const deletingTaskId = ref<number | null>(null)

watch(
  () => props.tasks,
  (tasks) => {
    if (stoppingTaskId.value === null) return
    const task = tasks.find((item) => item.task_id === stoppingTaskId.value)
    if (!task || (task.status !== TaskStatus.RUNNING && task.status !== TaskStatus.CLARIFYING)) {
      stoppingTaskId.value = null
    }
  },
  { deep: true },
)

const hasTasks = computed(() => props.tasks.length > 0)

function formatDate(value?: string | null) {
  return value ? new Date(value).toLocaleString() : '-'
}

async function stopTask(task: Task) {
  if (stoppingTaskId.value !== null) return
  stoppingTaskId.value = task.task_id
  try {
    await taskService.stopTask(task.task_id)
    emit('refresh')
  } catch (error: any) {
    stoppingTaskId.value = null
    ElMessage.error(error.response?.data?.detail || '停止任务失败')
  }
}

async function downloadTask(task: Task) {
  downloadingTaskId.value = task.task_id
  try {
    await taskService.downloadFile(task.task_id)
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '下载失败')
  } finally {
    downloadingTaskId.value = null
  }
}

async function deleteTask(task: Task) {
  try {
    await ElMessageBox.confirm(`确定要删除任务“${task.original_filename}”吗？`, '删除任务', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    deletingTaskId.value = task.task_id
    await taskService.deleteTask(task.task_id)
    emit('refresh')
    ElMessage.success('删除成功')
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error(error.response?.data?.detail || '删除失败')
  } finally {
    deletingTaskId.value = null
  }
}
</script>

<template>
  <section class="glass-card task-card">
    <div v-if="isLoading && !hasTasks" class="loading-state">
      <el-skeleton :rows="5" animated />
    </div>

    <el-empty v-else-if="!hasTasks" description="暂无任务，点击新建任务开始使用" />

    <el-table v-else :data="tasks" row-key="task_id" class="task-table">
      <el-table-column label="任务 ID" width="100">
        <template #default="{ row }">#{{ row.task_id }}</template>
      </el-table-column>
      <el-table-column label="文件名" min-width="220" show-overflow-tooltip prop="original_filename" />
      <el-table-column label="创建时间" min-width="180">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="完成时间" min-width="180">
        <template #default="{ row }">{{ formatDate(row.finished_at) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }"><StatusBadge :status="row.status" /></template>
      </el-table-column>
      <el-table-column label="操作" min-width="320" fixed="right">
        <template #default="{ row }">
          <div class="actions">
            <template v-if="row.status === TaskStatus.RUNNING">
              <el-button size="small" @click="emit('progress', row)">查看进度</el-button>
              <el-button
                size="small"
                type="danger"
                :loading="stoppingTaskId === row.task_id"
                @click="stopTask(row)"
              >停止</el-button>
            </template>

            <template v-else-if="row.status === TaskStatus.CLARIFYING">
              <el-button size="small" type="warning" @click="emit('clarify', row)">补充说明</el-button>
              <el-button
                size="small"
                type="danger"
                :loading="stoppingTaskId === row.task_id"
                @click="stopTask(row)"
              >停止</el-button>
            </template>

            <template v-else-if="row.status === TaskStatus.FINISHED">
              <el-button
                size="small"
                type="primary"
                :loading="downloadingTaskId === row.task_id"
                @click="downloadTask(row)"
              >下载结果</el-button>
              <el-button size="small" @click="emit('summary', row)">查看总结</el-button>
              <el-button
                size="small"
                type="danger"
                :loading="deletingTaskId === row.task_id"
                @click="deleteTask(row)"
              >删除</el-button>
            </template>

            <template v-else>
              <el-button
                size="small"
                type="danger"
                :loading="deletingTaskId === row.task_id"
                @click="deleteTask(row)"
              >删除</el-button>
            </template>
          </div>
          <div v-if="row.error_message" class="row-note error">错误：{{ row.error_message }}</div>
          <div v-if="row.status === TaskStatus.CLARIFYING" class="row-note clarify">需要澄清，请点击“补充说明”回复</div>
        </template>
      </el-table-column>
    </el-table>
  </section>
</template>

<style scoped>
.task-card { overflow: hidden; }
.loading-state { padding: 24px; }
.task-table { border-radius: var(--radius-md); overflow: hidden; }
.actions { display: flex; gap: 6px; flex-wrap: wrap; }
.actions :deep(.el-button + .el-button) { margin-left: 0; }
.row-note { margin-top: 8px; font-size: 12px; }
.error { color: var(--color-danger); }
.clarify { color: var(--color-warning); }
</style>

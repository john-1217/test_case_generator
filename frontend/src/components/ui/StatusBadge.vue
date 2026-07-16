<script setup lang="ts">
import { computed } from 'vue'
import { TaskStatus, type TaskStatus as TaskStatusValue } from '../../services/types'

const props = defineProps<{ status: TaskStatusValue }>()

const meta = computed(() => {
  switch (props.status) {
    case TaskStatus.RUNNING:
      return { label: '运行中', type: 'primary' as const }
    case TaskStatus.CLARIFYING:
      return { label: '待澄清', type: 'warning' as const }
    case TaskStatus.FINISHED:
      return { label: '已完成', type: 'success' as const }
    case TaskStatus.FAILED:
      return { label: '失败', type: 'danger' as const }
    default:
      return { label: '未知', type: 'info' as const }
  }
})
</script>

<template>
  <el-tag class="status-badge" :type="meta.type" effect="light">{{ meta.label }}</el-tag>
</template>

<style scoped>
.status-badge {
  min-width: 64px;
  justify-content: center;
  border-radius: 999px;
  font-size: 12px;
}
</style>

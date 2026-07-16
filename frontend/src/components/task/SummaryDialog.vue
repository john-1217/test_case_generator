<script setup lang="ts">
import { computed } from 'vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import type { Task } from '../../services/types'

const model = defineModel<boolean>({ required: true })
const props = defineProps<{ task: Task | null }>()

const markdown = computed(() => {
  const raw = props.task?.summary_content || ''
  return DOMPurify.sanitize(marked.parse(raw || '暂无总结内容', { async: false }) as string)
})
</script>

<template>
  <el-dialog v-model="model" title="测试总结" width="820px">
    <div v-if="task" class="markdown-body summary" v-html="markdown" />
    <el-empty v-else description="未选择任务" />
  </el-dialog>
</template>

<style scoped>
.summary { max-height: 68vh; overflow: auto; }
</style>

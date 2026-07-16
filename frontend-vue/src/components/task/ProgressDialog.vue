<script setup lang="ts">
import { computed } from 'vue'
import type { Task } from '../../services/types'

const model = defineModel<boolean>({ required: true })
const props = defineProps<{ task: Task | null }>()

const steps = [
  { key: 'doc_parsing', label: '文档解析' },
  { key: 'rag_retrieval', label: 'RAG 检索' },
  { key: 'phase1_analysis', label: 'Phase 1 需求分析' },
  { key: 'phase2_strategy', label: 'Phase 2 测试策略' },
  { key: 'phase3_generate', label: 'Phase 3 用例生成' },
  { key: 'phase4_summary', label: 'Phase 4 总结' },
  { key: 'extracting', label: '结果提取' },
]

const active = computed(() => {
  const idx = steps.findIndex((step) => step.key === props.task?.current_step)
  return idx >= 0 ? idx : 0
})
</script>

<template>
  <el-dialog v-model="model" title="工作流进度" width="560px">
    <el-empty v-if="!task" description="未选择任务" />
    <el-steps v-else direction="vertical" :active="active" finish-status="success" process-status="process">
      <el-step v-for="step in steps" :key="step.key" :title="step.label" :description="step.key" />
    </el-steps>
  </el-dialog>
</template>

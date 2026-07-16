<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { type Task, taskService } from '../../services/api'

const model = defineModel<boolean>({ required: true })
const props = defineProps<{ task: Task | null }>()
const emit = defineEmits<{ submitted: [] }>()

const input = ref('')
const isLoading = ref(false)

watch(model, (open) => {
  if (open) input.value = ''
})

const markdown = computed(() => {
  const raw = props.task?.clarification_message || ''
  return DOMPurify.sanitize(marked.parse(raw, { async: false }) as string)
})

async function submit(value?: string) {
  if (!props.task) return
  const text = value ?? input.value.trim()
  if (!text) {
    ElMessage.warning('请输入澄清内容')
    return
  }

  isLoading.value = true
  try {
    await taskService.clarifyTask(props.task.task_id, text)
    model.value = false
    emit('submitted')
    ElMessage.success('已提交澄清')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '提交澄清失败')
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <el-dialog v-model="model" title="需求澄清" width="720px">
    <div v-if="task" class="clarify-body">
      <div class="markdown-body" v-html="markdown" />
      <el-input
        v-model="input"
        type="textarea"
        :rows="6"
        placeholder="请输入补充说明或澄清答案"
      />
    </div>
    <el-empty v-else description="未选择任务" />

    <template #footer>
      <el-button :disabled="isLoading" @click="model = false">取消</el-button>
      <el-button :disabled="isLoading" @click="submit('忽略待澄清内容，继续生成')">忽略并继续</el-button>
      <el-button type="primary" :loading="isLoading" @click="submit()">提交澄清</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.clarify-body { display: flex; flex-direction: column; gap: 16px; }
.markdown-body {
  max-height: 320px;
  overflow: auto;
  padding: 14px;
  border-radius: var(--radius-md);
  background: rgba(79, 124, 255, 0.05);
}
</style>

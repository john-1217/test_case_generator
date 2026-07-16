<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete, Plus } from '@element-plus/icons-vue'
import { templateService, type Template, type TemplateField } from '../../services/api'

const model = defineModel<boolean>({ required: true })
const props = defineProps<{
  mode: 'create' | 'edit' | 'view'
  template: Template | null
}>()
const emit = defineEmits<{ saved: [] }>()

const isSaving = ref(false)
const form = reactive<{
  name: string
  fields: TemplateField[]
  isDefault: boolean
}>({
  name: '',
  fields: [{ name: '', description: '' }],
  isDefault: false,
})

const isViewMode = computed(() => props.mode === 'view')
const title = computed(() => {
  if (props.mode === 'view') return '查看模板'
  return props.mode === 'edit' ? '编辑模板' : '创建模板'
})

watch(
  () => [model.value, props.template, props.mode] as const,
  ([open]) => {
    if (!open) return
    form.name = props.template?.name ?? ''
    form.fields = props.template?.fields.map((field) => ({ ...field })) ?? [
      { name: '', description: '' },
    ]
    form.isDefault = props.template?.is_default ?? false
  },
  { immediate: true },
)

function addField() {
  form.fields.push({ name: '', description: '' })
}

function removeField(index: number) {
  form.fields.splice(index, 1)
  if (form.fields.length === 0) addField()
}

async function save() {
  const name = form.name.trim()
  const fields = form.fields.map((field) => ({
    name: field.name.trim(),
    description: field.description.trim(),
  }))

  if (!name) {
    ElMessage.warning('请输入模板名称')
    return
  }
  if (fields.length === 0 || fields.some((field) => !field.name)) {
    ElMessage.warning('请至少添加一个有效字段，并填写所有字段名称')
    return
  }

  isSaving.value = true
  try {
    if (props.mode === 'edit' && props.template) {
      await templateService.updateTemplate({
        id: props.template.id,
        name,
        fields,
        is_default: form.isDefault,
      })
      ElMessage.success('模板更新成功')
    } else {
      await templateService.createTemplate({
        name,
        fields,
        is_default: form.isDefault,
      })
      ElMessage.success('模板创建成功')
    }
    model.value = false
    emit('saved')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '保存模板失败')
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <el-dialog v-model="model" :title="title" width="680px" destroy-on-close>
    <el-form label-position="top" @submit.prevent="save">
      <el-form-item label="模板名称" required>
        <el-input
          v-model="form.name"
          :disabled="isViewMode"
          maxlength="100"
          show-word-limit
          placeholder="例如：API 测试模板"
        />
      </el-form-item>

      <el-form-item label="字段列表" required>
        <div class="field-list">
          <div v-for="(field, index) in form.fields" :key="index" class="field-row">
            <el-input
              v-model="field.name"
              :disabled="isViewMode"
              maxlength="100"
              placeholder="字段名称"
            />
            <el-input
              v-model="field.description"
              :disabled="isViewMode"
              maxlength="500"
              placeholder="字段描述"
            />
            <el-button
              v-if="!isViewMode"
              :icon="Delete"
              circle
              type="danger"
              plain
              aria-label="删除字段"
              @click="removeField(index)"
            />
          </div>
        </div>
        <el-button v-if="!isViewMode" :icon="Plus" plain @click="addField">添加字段</el-button>
      </el-form-item>

      <el-form-item v-if="!isViewMode">
        <el-checkbox v-model="form.isDefault">设为默认模板</el-checkbox>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="model = false">{{ isViewMode ? '关闭' : '取消' }}</el-button>
      <el-button v-if="!isViewMode" type="primary" :loading="isSaving" @click="save">
        保存模板
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.field-list {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;
}

.field-row {
  width: 100%;
  display: grid;
  grid-template-columns: minmax(150px, 0.8fr) minmax(220px, 1.4fr) auto;
  gap: 10px;
  align-items: center;
}

@media (max-width: 680px) {
  .field-row {
    grid-template-columns: 1fr;
  }
}
</style>

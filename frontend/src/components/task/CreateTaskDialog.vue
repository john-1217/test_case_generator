<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage, type UploadFile } from 'element-plus'
import {
  knowledgeService,
  llmConfigService,
  taskService,
  templateService,
  type ModelGroup,
  type Project,
  type Template,
} from '../../services/api'

const model = defineModel<boolean>({ required: true })
const emit = defineEmits<{ created: [] }>()

const LAST_SELECTED_MODEL_KEY = 'last_selected_model'

const file = ref<File | null>(null)
const outputFilename = ref('')
const templateId = ref<number | null>(null)
const selectedModel = ref('')
const selectedProjectId = ref<number | null>(null)
const templates = ref<Template[]>([])
const modelGroups = ref<ModelGroup[]>([])
const projects = ref<Project[]>([])
const isLoading = ref(false)
const isDataLoading = ref(false)

const availableProjects = computed(() => projects.value.filter((project) => project.doc_count > 0))

watch(model, async (open) => {
  if (open) {
    resetForm()
    await loadData()
  }
})

watch(selectedModel, (value) => {
  if (value) localStorage.setItem(LAST_SELECTED_MODEL_KEY, value)
})

function resetForm() {
  file.value = null
  outputFilename.value = ''
  templateId.value = null
  selectedModel.value = ''
  selectedProjectId.value = null
}

async function loadData() {
  isDataLoading.value = true
  try {
    const [templatesData, groupsData, projectsData] = await Promise.all([
      templateService.getTemplates(),
      llmConfigService.getModelGroups(),
      knowledgeService.getProjects(),
    ])

    templates.value = templatesData
    modelGroups.value = groupsData
    projects.value = projectsData.projects || []

    const lastSelected = localStorage.getItem(LAST_SELECTED_MODEL_KEY)
    if (lastSelected) {
      const [provider, selected] = lastSelected.split(':')
      const group = groupsData.find((g) => g.provider === provider)
      if (group?.models.includes(selected)) selectedModel.value = lastSelected
    }

    if (!selectedModel.value && groupsData[0]?.models[0]) {
      selectedModel.value = `${groupsData[0].provider}:${groupsData[0].models[0]}`
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '加载任务配置失败')
  } finally {
    isDataLoading.value = false
  }
}

function handleFileChange(uploadFile: UploadFile) {
  if (!uploadFile.raw) return
  file.value = uploadFile.raw
  if (!outputFilename.value) outputFilename.value = uploadFile.name.replace(/\.[^.]+$/, '')
}

function handleFileRemove() {
  file.value = null
}

async function submit() {
  if (!selectedModel.value) {
    ElMessage.warning('请选择模型')
    return
  }
  if (!file.value) {
    ElMessage.warning('请选择文件')
    return
  }
  if (!outputFilename.value.trim()) {
    ElMessage.warning('请输入输出文件名')
    return
  }

  const [provider, llmModel] = selectedModel.value.split(':')
  if (!provider || !llmModel) {
    ElMessage.error('无效的模型选择')
    return
  }

  isLoading.value = true
  try {
    const uploadRes = await taskService.uploadFile(file.value)
    await taskService.createTask({
      file_path: uploadRes.file_path,
      original_filename: uploadRes.original_filename,
      download_filename: outputFilename.value.trim(),
      template_id: templateId.value,
      provider,
      model: llmModel,
      project_id: selectedProjectId.value,
    })
    emit('created')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || error.message || '创建任务失败')
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <el-dialog v-model="model" title="新建任务" width="640px" destroy-on-close>
    <el-skeleton v-if="isDataLoading" :rows="6" animated />
    <el-form v-else label-position="top">
      <el-form-item label="模型选择 *">
        <el-select v-model="selectedModel" placeholder="请选择模型" filterable class="full-width">
          <el-option-group v-for="group in modelGroups" :key="group.provider" :label="group.name">
            <el-option
              v-for="item in group.models"
              :key="`${group.provider}:${item}`"
              :label="item"
              :value="`${group.provider}:${item}`"
            />
          </el-option-group>
        </el-select>
        <div v-if="modelGroups.length === 0" class="hint warning">暂无可用模型，请先配置模型提供商。</div>
      </el-form-item>

      <el-form-item label="上传文档 *">
        <el-upload
          drag
          :auto-upload="false"
          :limit="1"
          accept=".pdf,.doc,.docx,.txt,.md"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
          class="full-width"
        >
          <div class="upload-title">{{ file ? file.name : '点击或拖拽上传 PDF / DOC / DOCX / TXT / MD' }}</div>
        </el-upload>
      </el-form-item>

      <el-form-item label="输出文件名 *">
        <el-input v-model="outputFilename" placeholder="例如：需求测试用例" />
      </el-form-item>

      <el-form-item label="选择模板">
        <el-select v-model="templateId" clearable placeholder="默认模板" class="full-width">
          <el-option v-for="tpl in templates" :key="tpl.id" :label="`${tpl.name}${tpl.is_default ? '（默认）' : ''}`" :value="tpl.id" />
        </el-select>
      </el-form-item>

      <el-form-item label="关联知识库">
        <el-select v-model="selectedProjectId" clearable placeholder="不关联" class="full-width">
          <el-option
            v-for="project in availableProjects"
            :key="project.id"
            :label="`${project.name} (${project.doc_count} 个文档)`"
            :value="project.id"
          />
        </el-select>
        <div class="hint">关联知识库后，生成时会检索项目文档作为 RAG 上下文。</div>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button :disabled="isLoading" @click="model = false">取消</el-button>
      <el-button type="primary" :loading="isLoading" @click="submit">创建任务</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.full-width { width: 100%; }
.hint { margin-top: 6px; font-size: 12px; color: var(--color-text-muted); }
.warning { color: var(--color-warning); }
.upload-title { color: var(--color-text-secondary); }
</style>

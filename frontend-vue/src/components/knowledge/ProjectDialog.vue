<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  knowledgeService,
  type EmbeddingProviderInfo,
  type Project,
} from '../../services/api'

const model = defineModel<boolean>({ required: true })
const props = defineProps<{
  mode: 'create' | 'edit'
  project: Project | null
}>()
const emit = defineEmits<{ saved: [project: Project] }>()

const router = useRouter()
const providers = ref<EmbeddingProviderInfo[]>([])
const isLoadingProviders = ref(false)
const isSaving = ref(false)
const form = reactive({
  name: '',
  description: '',
  embeddingProvider: '',
  embeddingModel: '',
})

const title = computed(() => (props.mode === 'edit' ? '编辑知识库项目' : '创建知识库项目'))
const configuredProviders = computed(() => providers.value.filter((provider) => provider.is_configured))
const embeddingLocked = computed(() => props.mode === 'edit' && (props.project?.doc_count ?? 0) > 0)

watch(
  () => [model.value, props.project, props.mode] as const,
  async ([open]) => {
    if (!open) return
    form.name = props.project?.name ?? ''
    form.description = props.project?.description ?? ''
    form.embeddingProvider = props.project?.embedding_provider ?? ''
    form.embeddingModel = props.project?.embedding_model ?? ''
    await loadProviders()

    if (props.mode === 'create' && !form.embeddingProvider) {
      const first = configuredProviders.value[0]
      if (first) {
        form.embeddingProvider = first.provider
        form.embeddingModel = first.default_model
      }
    }
  },
)

async function loadProviders() {
  isLoadingProviders.value = true
  try {
    providers.value = await knowledgeService.getEmbeddingProviders()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '加载 Embedding 厂商失败')
  } finally {
    isLoadingProviders.value = false
  }
}

function handleProviderChange(provider: string) {
  const info = providers.value.find((item) => item.provider === provider)
  if (info) form.embeddingModel = info.default_model
}

async function goToLlmConfig() {
  model.value = false
  await router.push('/llm')
}

async function save() {
  const name = form.name.trim()
  const description = form.description.trim()
  const embeddingProvider = form.embeddingProvider
  const embeddingModel = form.embeddingModel.trim()

  if (!name) {
    ElMessage.warning('请输入项目名称')
    return
  }
  if (!embeddingProvider) {
    ElMessage.warning('请选择 Embedding 厂商')
    return
  }
  if (!embeddingModel) {
    ElMessage.warning('请输入 Embedding 模型')
    return
  }

  isSaving.value = true
  try {
    let project: Project
    if (props.mode === 'edit' && props.project) {
      project = await knowledgeService.updateProject(props.project.id, {
        name,
        description,
        embedding_provider: embeddingProvider,
        embedding_model: embeddingModel,
      })
      ElMessage.success('知识库项目更新成功')
    } else {
      project = await knowledgeService.createProject({
        name,
        description: description || undefined,
        embedding_provider: embeddingProvider,
        embedding_model: embeddingModel,
      })
      ElMessage.success('知识库项目创建成功')
    }
    model.value = false
    emit('saved', project)
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '保存知识库项目失败')
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <el-dialog v-model="model" :title="title" width="600px" destroy-on-close>
    <el-form label-position="top" @submit.prevent="save">
      <el-form-item label="项目名称" required>
        <el-input
          v-model="form.name"
          maxlength="255"
          show-word-limit
          placeholder="例如：CRM 系统 V2.0"
        />
      </el-form-item>

      <el-form-item label="项目描述">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="3"
          maxlength="1000"
          show-word-limit
          placeholder="描述项目的业务背景和范围"
        />
      </el-form-item>

      <el-alert
        v-if="!isLoadingProviders && configuredProviders.length === 0"
        type="warning"
        :closable="false"
        show-icon
        class="provider-alert"
      >
        <template #title>暂无已配置且支持 Embedding 的厂商</template>
        <el-link type="primary" @click="goToLlmConfig">前往模型配置</el-link>
      </el-alert>

      <el-form-item label="Embedding 厂商" required>
        <el-select
          v-model="form.embeddingProvider"
          class="full-width"
          :loading="isLoadingProviders"
          :disabled="embeddingLocked || configuredProviders.length === 0"
          placeholder="请选择厂商"
          @change="handleProviderChange"
        >
          <el-option
            v-for="provider in configuredProviders"
            :key="provider.provider"
            :label="provider.name"
            :value="provider.provider"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="Embedding 模型" required>
        <el-input
          v-model="form.embeddingModel"
          :disabled="embeddingLocked"
          maxlength="200"
          placeholder="例如：text-embedding-3-small"
        />
        <div v-if="embeddingLocked" class="field-hint">
          项目已有文档，删除全部文档后才能修改 Embedding 配置。
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="model = false">取消</el-button>
      <el-button
        type="primary"
        :loading="isSaving"
        :disabled="props.mode === 'create' && configuredProviders.length === 0"
        @click="save"
      >保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.full-width {
  width: 100%;
}

.provider-alert {
  margin-bottom: 18px;
}

.field-hint {
  margin-top: 6px;
  color: var(--color-warning);
  font-size: 12px;
  line-height: 1.5;
}
</style>

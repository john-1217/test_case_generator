<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Hide, View } from '@element-plus/icons-vue'
import { llmConfigService, type ProviderConfig, type ProviderListItem } from '../services/api'

import openaiLogo from '../assets/images/openai.png'
import geminiLogo from '../assets/images/gemini.png'
import anthropicLogo from '../assets/images/anthropic.png'
import deepseekLogo from '../assets/images/deepseek.png'
import kimiLogo from '../assets/images/kimi.png'
import openrouterLogo from '../assets/images/openrouter.png'

type StatusObj = { type: 'success' | 'error' | 'loading'; message: string }

const PROVIDER_LOGOS: Record<string, string> = {
  openai: openaiLogo,
  gemini: geminiLogo,
  anthropic: anthropicLogo,
  deepseek: deepseekLogo,
  kimi: kimiLogo,
  openrouter: openrouterLogo,
}

const PROVIDER_GRADIENTS: Record<string, string> = {
  openai: '#000000',
  gemini: '#ffffff',
  anthropic: '#ffffff',
  deepseek: '#ffffff',
  kimi: '#000000',
  openrouter: '#000000',
}

const PROVIDER_DEFAULT_URLS: Record<string, string> = {
  openai: 'https://api.openai.com',
  gemini: 'https://generativelanguage.googleapis.com',
  anthropic: 'https://api.anthropic.com',
  deepseek: 'https://api.deepseek.com',
  kimi: 'https://api.moonshot.cn',
  openrouter: 'https://openrouter.ai/api',
}

const providers = ref<ProviderListItem[]>([])
const selectedProvider = ref<string | null>(null)
const config = ref<ProviderConfig | null>(null)
const baseUrl = ref('')
const apiKey = ref('')
const showApiKey = ref(false)
const newModelName = ref('')
const isLoadingProviders = ref(false)
const isLoadingConfig = ref(false)
const savePending = ref(false)
const fetchPending = ref(false)
const modelTestStatus = ref<Record<string, StatusObj>>({})
const fetchStatus = ref<StatusObj | null>(null)
const saveStatus = ref<StatusObj | null>(null)

const currentProviderInfo = computed(() =>
  providers.value.find((provider) => provider.provider === selectedProvider.value) || null,
)
const isNewConfig = computed(() => config.value === null)
const canEditBaseUrl = computed(() => selectedProvider.value === 'openai')

onMounted(() => {
  loadProviders()
})

watch(selectedProvider, async (provider) => {
  resetTransientState()
  if (provider) await loadConfig(provider)
})

function resetTransientState() {
  apiKey.value = ''
  showApiKey.value = false
  newModelName.value = ''
  modelTestStatus.value = {}
  fetchStatus.value = null
  saveStatus.value = null
}

function providerLogo(provider: string) {
  return PROVIDER_LOGOS[provider]
}

function providerGradient(provider: string) {
  return PROVIDER_GRADIENTS[provider] || 'linear-gradient(135deg, #6b7280, #374151)'
}

function providerFallback(provider: string) {
  return provider.slice(0, 2).toUpperCase()
}

function statusText(provider: ProviderListItem | null, providerConfig: ProviderConfig | null) {
  if (providerConfig?.is_available || provider?.is_available) return '✓ 连接正常'
  if (providerConfig || provider?.is_configured) return '配置已保存'
  return '未配置'
}

function autoClearStatus(target: 'save' | 'fetch', delay = 2000) {
  window.setTimeout(() => {
    if (target === 'save') saveStatus.value = null
    if (target === 'fetch') fetchStatus.value = null
  }, delay)
}

async function loadProviders() {
  isLoadingProviders.value = true
  try {
    const data = await llmConfigService.getProviderList()
    providers.value = data

    if (!selectedProvider.value && data.length > 0) {
      const configured = data.find((provider) => provider.is_configured)
      selectedProvider.value = configured?.provider || data[0].provider
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '加载模型提供商失败')
  } finally {
    isLoadingProviders.value = false
  }
}

async function loadConfig(provider: string) {
  isLoadingConfig.value = true
  try {
    const data = await llmConfigService.getProviderConfig(provider)
    config.value = data
    baseUrl.value = data?.base_url || PROVIDER_DEFAULT_URLS[provider] || ''
    apiKey.value = ''
  } catch {
    config.value = null
    baseUrl.value = PROVIDER_DEFAULT_URLS[provider] || ''
    apiKey.value = ''
  } finally {
    isLoadingConfig.value = false
  }
}

function validateConfigAction(requireKeyForNew = true) {
  if (!selectedProvider.value) {
    ElMessage.warning('请先选择提供商')
    return false
  }
  if (!baseUrl.value.trim()) {
    ElMessage.warning('请填写 Base URL')
    return false
  }
  if (requireKeyForNew && isNewConfig.value && !apiKey.value.trim()) {
    ElMessage.warning('请填写 API Key')
    return false
  }
  return true
}

async function handleSave() {
  if (!validateConfigAction(true) || !selectedProvider.value) return

  savePending.value = true
  saveStatus.value = { type: 'loading', message: '保存中...' }
  try {
    await llmConfigService.saveProviderConfig(selectedProvider.value, {
      base_url: baseUrl.value.trim(),
      api_key: apiKey.value.trim(),
    })
    saveStatus.value = { type: 'success', message: '保存成功，请重新测试模型连接' }
    await Promise.all([loadProviders(), loadConfig(selectedProvider.value)])
    autoClearStatus('save')
  } catch (error: any) {
    saveStatus.value = { type: 'error', message: error.response?.data?.detail || '保存失败' }
  } finally {
    savePending.value = false
  }
}

async function handleFetchModels() {
  if (!validateConfigAction(true) || !selectedProvider.value) return

  fetchPending.value = true
  fetchStatus.value = { type: 'loading', message: '获取中...' }
  try {
    const result = await llmConfigService.fetchModels(selectedProvider.value, {
      base_url: baseUrl.value.trim(),
      api_key: apiKey.value.trim(),
    })
    fetchStatus.value = {
      type: result.success ? 'success' : 'error',
      message: result.success ? `获取到 ${result.models.length} 个模型` : result.message || '获取失败',
    }
    if (result.success) {
      await Promise.all([loadProviders(), loadConfig(selectedProvider.value)])
      autoClearStatus('fetch')
    }
  } catch (error: any) {
    fetchStatus.value = { type: 'error', message: error.response?.data?.detail || '获取模型列表失败' }
  } finally {
    fetchPending.value = false
  }
}

async function handleAddModel() {
  const modelName = newModelName.value.trim()
  if (!selectedProvider.value || !modelName) return

  try {
    await llmConfigService.addModel(selectedProvider.value, modelName)
    newModelName.value = ''
    await Promise.all([loadProviders(), loadConfig(selectedProvider.value)])
    ElMessage.success('模型已添加')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '添加模型失败')
  }
}

async function handleDeleteModel(modelName: string) {
  if (!selectedProvider.value) return

  try {
    await ElMessageBox.confirm(`确定要删除模型“${modelName}”吗？`, '删除模型', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await llmConfigService.deleteModel(selectedProvider.value, modelName)
    await Promise.all([loadProviders(), loadConfig(selectedProvider.value)])
    ElMessage.success('模型已删除')
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error(error.response?.data?.detail || '删除模型失败')
  }
}

async function handleTestModel(modelName: string) {
  if (!validateConfigAction(true) || !selectedProvider.value) return

  modelTestStatus.value = {
    ...modelTestStatus.value,
    [modelName]: { type: 'loading', message: '测试中...' },
  }

  try {
    const result = await llmConfigService.testModel(selectedProvider.value, modelName, {
      base_url: baseUrl.value.trim(),
      api_key: apiKey.value.trim(),
    })
    modelTestStatus.value = {
      ...modelTestStatus.value,
      [modelName]: { type: result.success ? 'success' : 'error', message: result.message },
    }

    if (result.success) {
      await loadProviders()
      window.setTimeout(() => {
        const next = { ...modelTestStatus.value }
        delete next[modelName]
        modelTestStatus.value = next
      }, 3000)
    }
  } catch (error: any) {
    modelTestStatus.value = {
      ...modelTestStatus.value,
      [modelName]: { type: 'error', message: error.response?.data?.detail || '测试失败' },
    }
  }
}
</script>

<template>
  <section class="llm-config glass-card">
    <div class="page-header">
      <div>
        <h2>模型配置</h2>
        <p>配置 LLM 提供商、同步模型列表并测试连接。</p>
      </div>
      <el-button :loading="isLoadingProviders" @click="loadProviders">刷新提供商</el-button>
    </div>

    <div class="layout">
      <aside class="provider-list">
        <el-skeleton v-if="isLoadingProviders && providers.length === 0" :rows="6" animated />
        <button
          v-for="provider in providers"
          v-else
          :key="provider.provider"
          class="provider-item"
          :class="{ active: selectedProvider === provider.provider, configured: provider.is_configured }"
          @click="selectedProvider = provider.provider"
        >
          <div class="provider-icon" :style="{ background: providerGradient(provider.provider) }">
            <img v-if="providerLogo(provider.provider)" :src="providerLogo(provider.provider)" :alt="provider.name" />
            <span v-else class="logo-text">{{ providerFallback(provider.provider) }}</span>
          </div>
          <div class="provider-copy">
            <span class="provider-name">{{ provider.name }}</span>
            <small>{{ provider.model_count }} 个模型</small>
          </div>
          <span
            class="status-dot"
            :class="provider.is_available ? 'available' : provider.is_configured ? 'configured' : 'unconfigured'"
          />
        </button>
      </aside>

      <main class="config-panel">
        <el-empty v-if="!selectedProvider" description="请从左侧选择一个提供商进行配置" />
        <el-skeleton v-else-if="isLoadingConfig" :rows="8" animated />

        <template v-else>
          <div class="config-header">
            <div class="provider-icon large" :style="{ background: providerGradient(selectedProvider) }">
              <img v-if="providerLogo(selectedProvider)" :src="providerLogo(selectedProvider)" :alt="selectedProvider" />
              <span v-else class="logo-text">{{ providerFallback(selectedProvider) }}</span>
            </div>
            <div>
              <h3>{{ currentProviderInfo?.name || selectedProvider }}</h3>
              <p>{{ statusText(currentProviderInfo, config) }}</p>
            </div>
          </div>

          <div class="form-card">
            <div class="field">
              <label>
                Base URL
                <span v-if="!canEditBaseUrl" class="muted">（固定）</span>
              </label>
              <el-input
                v-model="baseUrl"
                :disabled="!canEditBaseUrl"
                :readonly="!canEditBaseUrl"
                placeholder="https://api.openai.com"
              />
              <small v-if="canEditBaseUrl" class="hint">OpenAI 兼容接口请填写 host，不要额外追加 /v1。</small>
            </div>

            <div class="field">
              <label>API Key</label>
              <el-input
                v-model="apiKey"
                :type="showApiKey ? 'text' : 'password'"
                :placeholder="config ? '（保持不变请留空）' : 'sk-...'"
                autocomplete="off"
              >
                <template #suffix>
                  <el-icon class="toggle-icon" @click="showApiKey = !showApiKey">
                    <View v-if="!showApiKey" />
                    <Hide v-else />
                  </el-icon>
                </template>
              </el-input>
            </div>

            <div class="actions">
              <el-button type="primary" :loading="savePending" @click="handleSave">保存配置</el-button>
              <el-button :loading="fetchPending" @click="handleFetchModels">获取模型列表</el-button>
            </div>

            <div v-if="saveStatus" class="status-msg" :class="saveStatus.type">{{ saveStatus.message }}</div>
            <div v-if="fetchStatus" class="status-msg" :class="fetchStatus.type">{{ fetchStatus.message }}</div>
          </div>

          <div class="model-section">
            <div class="section-header">
              <h4>模型列表</h4>
              <span>{{ config?.models.length || 0 }} 个模型</span>
            </div>

            <div class="add-model-row">
              <el-input
                v-model="newModelName"
                placeholder="添加自定义模型名称，例如 openai/gpt-4o"
                @keydown.enter="handleAddModel"
              />
              <el-button @click="handleAddModel">添加</el-button>
            </div>

            <div v-if="!config?.models.length" class="empty-models">
              暂无模型。请使用“获取模型列表”或手动添加。
            </div>

            <div v-else class="model-list">
              <div v-for="model in config.models" :key="model.id" class="model-item">
                <div class="model-main">
                  <span class="model-name" :class="{ custom: model.is_custom }">{{ model.model_name }}</span>
                  <el-tag v-if="model.is_custom" size="small" type="primary" effect="plain">自定义</el-tag>
                </div>

                <div class="model-actions">
                  <el-tooltip :content="modelTestStatus[model.model_name]?.message || '测试模型连接'">
                    <el-button
                      size="small"
                      :type="modelTestStatus[model.model_name]?.type === 'success'
                        ? 'success'
                        : modelTestStatus[model.model_name]?.type === 'error'
                          ? 'danger'
                          : 'default'"
                      :loading="modelTestStatus[model.model_name]?.type === 'loading'"
                      @click="handleTestModel(model.model_name)"
                    >
                      测试
                    </el-button>
                  </el-tooltip>
                  <el-button size="small" type="danger" plain @click="handleDeleteModel(model.model_name)">
                    删除
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </template>
      </main>
    </div>
  </section>
</template>

<style scoped>
.llm-config {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
}

.page-header p {
  margin: 6px 0 0;
  color: var(--color-text-secondary);
}

.layout {
  display: grid;
  grid-template-columns: 250px minmax(0, 1fr);
  gap: 22px;
}

.provider-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.provider-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  cursor: pointer;
  color: var(--color-text-primary);
  text-align: left;
  transition: background-color 0.2s ease, border-color 0.2s ease;
}

.provider-item:hover {
  border-color: #b2ccff;
  background: var(--color-primary-light);
}

.provider-item.active {
  border-color: #84adfa;
  background: var(--color-primary-light);
  color: var(--color-primary-dark);
}

.provider-item.configured:not(.active) {
  border-color: #a6f4c5;
}

.provider-icon {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  flex-shrink: 0;
}

.provider-icon.large {
  width: 48px;
  height: 48px;
  border-radius: 14px;
}

.provider-icon img {
  width: 24px;
  height: 24px;
  object-fit: contain;
}

.provider-icon.large img {
  width: 32px;
  height: 32px;
}

.logo-text {
  font-size: 11px;
  font-weight: 700;
  color: #fff;
}

.provider-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.provider-name {
  font-weight: 600;
}

.provider-copy small {
  color: var(--color-text-muted);
}

.provider-item.active .provider-copy small {
  color: var(--color-primary-dark);
}

.status-dot {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  margin-left: auto;
  flex-shrink: 0;
}

.status-dot.available {
  background: var(--color-success);
}

.status-dot.configured {
  background: var(--color-warning);
}

.status-dot.unconfigured {
  background: #cbd5e1;
}

.config-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-width: 0;
}

.config-header {
  display: flex;
  align-items: center;
  gap: 14px;
}

.config-header h3 {
  margin: 0;
  font-size: 22px;
}

.config-header p {
  margin: 4px 0 0;
  color: var(--color-text-secondary);
}

.form-card,
.model-section {
  padding: 20px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
}

.form-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.field label,
.section-header h4 {
  font-weight: 700;
}

.muted,
.hint {
  color: var(--color-text-muted);
}

.hint {
  font-size: 12px;
}

.toggle-icon {
  cursor: pointer;
}

.actions,
.add-model-row,
.model-actions {
  display: flex;
  gap: 10px;
}

.status-msg {
  padding: 9px 12px;
  border-radius: var(--radius-sm);
  font-size: 14px;
}

.status-msg.success {
  background: rgba(16, 185, 129, 0.12);
  color: var(--color-success);
}

.status-msg.error {
  background: rgba(239, 68, 68, 0.1);
  color: var(--color-danger);
}

.status-msg.loading {
  background: rgba(79, 124, 255, 0.1);
  color: var(--color-primary);
}

.model-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-header h4 {
  margin: 0;
  font-size: 17px;
}

.section-header span,
.empty-models {
  color: var(--color-text-secondary);
}

.model-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 420px;
  overflow: auto;
}

.model-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-muted);
}

.model-main {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.model-name.custom {
  color: var(--color-primary);
}

.empty-models {
  padding: 26px;
  text-align: center;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
}

@media (max-width: 900px) {
  .layout { grid-template-columns: 1fr; }
  .provider-list {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  }
}

@media (max-width: 640px) {
  .llm-config { padding: 18px; }
  .page-header,
  .section-header,
  .model-item { align-items: flex-start; flex-direction: column; }
  .add-model-row { align-items: stretch; flex-direction: column; }
  .model-actions { width: 100%; }
}
</style>

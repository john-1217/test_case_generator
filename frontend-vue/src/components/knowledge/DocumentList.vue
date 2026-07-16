<script setup lang="ts">
import { ref } from 'vue'
import { Delete, Refresh, Upload } from '@element-plus/icons-vue'
import type { KnowledgeDocument } from '../../services/api'

const props = defineProps<{
  documents: KnowledgeDocument[]
  isLoading: boolean
  isUploading: boolean
}>()
const emit = defineEmits<{
  upload: [file: File]
  refresh: []
  delete: [document: KnowledgeDocument]
}>()

const fileInput = ref<HTMLInputElement | null>(null)

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(value: string) {
  return new Date(value).toLocaleString()
}

function statusType(status: KnowledgeDocument['status']): 'info' | 'success' | 'danger' {
  if (status === 'ready') return 'success'
  if (status === 'failed') return 'danger'
  return 'info'
}

function statusText(document: KnowledgeDocument) {
  if (document.status === 'ready') return `已就绪 · ${document.chunk_count} 个分块`
  if (document.status === 'failed') return '处理失败'
  return '处理中'
}

function selectFile() {
  fileInput.value?.click()
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) emit('upload', file)
  input.value = ''
}
</script>

<template>
  <section class="document-section">
    <div class="section-header">
      <div>
        <h3>文档列表</h3>
        <span>{{ documents.length }} 个上传记录</span>
      </div>
      <div class="actions">
        <input
          ref="fileInput"
          type="file"
          class="hidden-input"
          accept=".pdf,.doc,.docx,.txt,.md"
          @change="handleFileChange"
        />
        <el-button :icon="Refresh" :loading="isLoading" @click="emit('refresh')">刷新</el-button>
        <el-button type="primary" :icon="Upload" :loading="isUploading" @click="selectFile">
          上传文档
        </el-button>
      </div>
    </div>

    <div v-if="isLoading && documents.length === 0" class="loading-state">
      <el-skeleton :rows="4" animated />
    </div>

    <el-empty v-else-if="documents.length === 0" description="暂无文档，上传项目文档以构建知识库" />

    <div v-else class="document-list">
      <article v-for="document in documents" :key="document.id" class="document-item">
        <div class="document-main">
          <div class="document-name">{{ document.original_filename }}</div>
          <div class="document-meta">
            <span>{{ formatFileSize(document.file_size) }}</span>
            <span>{{ formatDate(document.created_at) }}</span>
          </div>
        </div>

        <div class="document-actions">
          <el-tooltip
            :disabled="!document.error_message"
            :content="document.error_message || ''"
            placement="top"
          >
            <el-tag :type="statusType(document.status)" :effect="document.status === 'processing' ? 'plain' : 'light'">
              {{ statusText(document) }}
            </el-tag>
          </el-tooltip>
          <el-button
            :icon="Delete"
            circle
            type="danger"
            plain
            aria-label="删除文档"
            @click="emit('delete', document)"
          />
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.document-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-header,
.section-header > div,
.actions,
.document-item,
.document-actions {
  display: flex;
  align-items: center;
}

.section-header,
.document-item {
  justify-content: space-between;
  gap: 18px;
}

.section-header h3 {
  margin: 0;
  font-size: 17px;
}

.section-header span,
.document-meta {
  color: var(--color-text-secondary);
  font-size: 12px;
}

.section-header > div:first-child {
  align-items: baseline;
  gap: 10px;
}

.actions,
.document-actions {
  gap: 8px;
}

.hidden-input {
  display: none;
}

.loading-state {
  padding: 18px 0;
}

.document-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.document-item {
  padding: 14px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-strong);
}

.document-main {
  min-width: 0;
}

.document-name {
  overflow: hidden;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.document-meta {
  display: flex;
  gap: 14px;
  margin-top: 6px;
}

@media (max-width: 760px) {
  .section-header,
  .document-item {
    align-items: flex-start;
    flex-direction: column;
  }

  .document-actions {
    width: 100%;
    justify-content: space-between;
  }
}
</style>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Plus, Refresh } from '@element-plus/icons-vue'
import DocumentList from '../components/knowledge/DocumentList.vue'
import ProjectDialog from '../components/knowledge/ProjectDialog.vue'
import {
  knowledgeService,
  type KnowledgeDocument,
  type Project,
} from '../services/api'

const projects = ref<Project[]>([])
const selectedProjectId = ref<number | null>(null)
const documents = ref<KnowledgeDocument[]>([])
const isLoadingProjects = ref(false)
const isLoadingDocuments = ref(false)
const isUploading = ref(false)
const projectDialogOpen = ref(false)
const projectDialogMode = ref<'create' | 'edit'>('create')

let pollTimer: ReturnType<typeof setInterval> | null = null
let pollingRequest = false

const selectedProject = computed(
  () => projects.value.find((project) => project.id === selectedProjectId.value) ?? null,
)

onMounted(loadProjects)
onUnmounted(stopDocumentPolling)

watch(selectedProjectId, async (projectId) => {
  stopDocumentPolling()
  documents.value = []
  if (projectId !== null) await loadDocuments(projectId)
})

async function loadProjects(selectId?: number) {
  isLoadingProjects.value = true
  try {
    const data = await knowledgeService.getProjects()
    projects.value = data.projects

    if (selectId !== undefined) {
      selectedProjectId.value = selectId
    } else if (
      selectedProjectId.value !== null &&
      !projects.value.some((project) => project.id === selectedProjectId.value)
    ) {
      selectedProjectId.value = null
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '加载知识库项目失败')
  } finally {
    isLoadingProjects.value = false
  }
}

async function loadDocuments(projectId = selectedProjectId.value) {
  if (projectId === null) return
  isLoadingDocuments.value = true
  try {
    const data = await knowledgeService.getDocuments(projectId)
    if (selectedProjectId.value !== projectId) return
    documents.value = data
    if (data.some((document) => document.status === 'processing')) startDocumentPolling()
    else stopDocumentPolling()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '加载知识库文档失败')
  } finally {
    isLoadingDocuments.value = false
  }
}

function startDocumentPolling() {
  if (pollTimer) return
  pollTimer = setInterval(async () => {
    const projectId = selectedProjectId.value
    if (projectId === null || pollingRequest) return

    pollingRequest = true
    try {
      const data = await knowledgeService.getDocuments(projectId)
      if (selectedProjectId.value !== projectId) return
      documents.value = data
      if (!data.some((document) => document.status === 'processing')) {
        stopDocumentPolling()
        await loadProjects()
      }
    } catch (error) {
      console.error('Failed to poll knowledge documents', error)
    } finally {
      pollingRequest = false
    }
  }, 3000)
}

function stopDocumentPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function openProjectDialog(mode: 'create' | 'edit') {
  projectDialogMode.value = mode
  projectDialogOpen.value = true
}

async function handleProjectSaved(project: Project) {
  await loadProjects(project.id)
}

async function deleteProject(project: Project) {
  try {
    await ElMessageBox.confirm(
      `确定要删除项目“${project.name}”吗？所有关联文档和向量数据都将被永久删除。`,
      '删除知识库项目',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      },
    )
    await knowledgeService.deleteProject(project.id)
    if (selectedProjectId.value === project.id) selectedProjectId.value = null
    await loadProjects()
    ElMessage.success('知识库项目已删除')
  } catch (error: any) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(error.response?.data?.detail || '删除知识库项目失败')
    }
  }
}

async function uploadDocument(file: File) {
  const project = selectedProject.value
  if (!project) return

  isUploading.value = true
  try {
    await knowledgeService.uploadDocument(project.id, file)
    ElMessage.success('文档上传成功，正在后台处理')
    await Promise.all([loadDocuments(project.id), loadProjects()])
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '上传文档失败')
  } finally {
    isUploading.value = false
  }
}

async function deleteDocument(document: KnowledgeDocument) {
  try {
    await ElMessageBox.confirm(`确定要删除文档“${document.original_filename}”吗？`, '删除文档', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await knowledgeService.deleteDocument(document.id)
    await Promise.all([loadDocuments(), loadProjects()])
    ElMessage.success('文档已删除')
  } catch (error: any) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(error.response?.data?.detail || '删除文档失败')
    }
  }
}

async function refreshSelectedProject() {
  await Promise.all([loadDocuments(), loadProjects()])
}
</script>

<template>
  <section class="knowledge-view">
    <div class="page-header glass-card">
      <div>
        <h2>知识库管理</h2>
        <p>管理项目文档，为测试用例生成提供检索上下文。</p>
      </div>
      <div class="header-actions">
        <el-button :icon="Refresh" :loading="isLoadingProjects" @click="loadProjects()">刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="openProjectDialog('create')">创建项目</el-button>
      </div>
    </div>

    <div v-if="isLoadingProjects && projects.length === 0" class="glass-card loading-card">
      <el-skeleton :rows="7" animated />
    </div>

    <div v-else-if="projects.length === 0" class="glass-card empty-card">
      <el-empty description="还没有知识库项目">
        <el-button type="primary" :icon="Plus" @click="openProjectDialog('create')">
          创建第一个项目
        </el-button>
      </el-empty>
    </div>

    <div v-else class="knowledge-layout">
      <aside class="glass-card project-panel">
        <div class="panel-title">项目列表</div>
        <button
          v-for="project in projects"
          :key="project.id"
          type="button"
          class="project-item"
          :class="{ active: selectedProjectId === project.id }"
          @click="selectedProjectId = project.id"
        >
          <span class="project-name">{{ project.name }}</span>
          <span class="project-meta">
            {{ project.embedding_provider }} · {{ project.doc_count }} 个文档
          </span>
        </button>
      </aside>

      <main class="glass-card detail-panel">
        <el-empty v-if="!selectedProject" description="选择左侧项目查看详情" />

        <template v-else>
          <div class="detail-header">
            <div>
              <h3>{{ selectedProject.name }}</h3>
              <p>{{ selectedProject.description || '暂无项目描述' }}</p>
            </div>
            <div class="detail-actions">
              <el-button :icon="Edit" @click="openProjectDialog('edit')">编辑项目</el-button>
              <el-button type="danger" plain :icon="Delete" @click="deleteProject(selectedProject)">
                删除项目
              </el-button>
            </div>
          </div>

          <div class="project-info">
            <div>
              <span>Embedding 厂商</span>
              <strong>{{ selectedProject.embedding_provider }}</strong>
            </div>
            <div>
              <span>Embedding 模型</span>
              <strong>{{ selectedProject.embedding_model }}</strong>
            </div>
            <div>
              <span>就绪文档</span>
              <strong>{{ selectedProject.doc_count }}</strong>
            </div>
          </div>

          <el-divider />

          <DocumentList
            :documents="documents"
            :is-loading="isLoadingDocuments"
            :is-uploading="isUploading"
            @upload="uploadDocument"
            @refresh="refreshSelectedProject"
            @delete="deleteDocument"
          />
        </template>
      </main>
    </div>

    <ProjectDialog
      v-model="projectDialogOpen"
      :mode="projectDialogMode"
      :project="projectDialogMode === 'edit' ? selectedProject : null"
      @saved="handleProjectSaved"
    />
  </section>
</template>

<style scoped>
.knowledge-view {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-header,
.detail-header,
.header-actions,
.detail-actions {
  display: flex;
  align-items: center;
}

.page-header,
.detail-header {
  justify-content: space-between;
  gap: 20px;
}

.page-header {
  padding: 24px;
}

h2,
h3,
p {
  margin: 0;
}

.page-header h2 {
  font-size: 24px;
}

.page-header p,
.detail-header p {
  margin-top: 6px;
  color: var(--color-text-secondary);
}

.header-actions,
.detail-actions {
  gap: 10px;
}

.loading-card,
.empty-card {
  padding: 32px;
}

.knowledge-layout {
  display: grid;
  grid-template-columns: minmax(230px, 280px) minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.project-panel,
.detail-panel {
  padding: 18px;
}

.project-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.panel-title {
  padding: 4px 8px 10px;
  font-weight: 700;
}

.project-item {
  width: 100%;
  padding: 13px 14px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-text-primary);
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
}

.project-item:hover {
  border-color: #b2ccff;
  background: var(--color-primary-light);
}

.project-item.active {
  border-color: #84adfa;
  background: var(--color-primary-light);
  color: var(--color-primary-dark);
}

.project-name,
.project-meta {
  display: block;
}

.project-name {
  overflow: hidden;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-meta {
  margin-top: 5px;
  color: var(--color-text-secondary);
  font-size: 12px;
}

.detail-panel {
  min-height: 430px;
}

.detail-header {
  align-items: flex-start;
}

.detail-header h3 {
  font-size: 21px;
}

.project-info {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 20px;
}

.project-info > div {
  padding: 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-muted);
}

.project-info span,
.project-info strong {
  display: block;
}

.project-info span {
  margin-bottom: 6px;
  color: var(--color-text-secondary);
  font-size: 12px;
}

.project-info strong {
  overflow-wrap: anywhere;
}

@media (max-width: 900px) {
  .knowledge-layout {
    grid-template-columns: 1fr;
  }

  .project-panel {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  }

  .panel-title {
    grid-column: 1 / -1;
  }
}

@media (max-width: 760px) {
  .page-header,
  .detail-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .project-info {
    grid-template-columns: 1fr;
  }
}
</style>

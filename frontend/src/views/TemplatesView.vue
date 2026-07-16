<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Plus, Star, View } from '@element-plus/icons-vue'
import TemplateDialog from '../components/template/TemplateDialog.vue'
import { templateService, type Template } from '../services/api'

const templates = ref<Template[]>([])
const isLoading = ref(false)
const dialogOpen = ref(false)
const dialogMode = ref<'create' | 'edit' | 'view'>('create')
const selectedTemplate = ref<Template | null>(null)
const deletingId = ref<number | null>(null)

onMounted(loadTemplates)

async function loadTemplates() {
  isLoading.value = true
  try {
    templates.value = await templateService.getTemplates()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '加载模板失败')
  } finally {
    isLoading.value = false
  }
}

function openDialog(mode: 'create' | 'edit' | 'view', template: Template | null = null) {
  dialogMode.value = mode
  selectedTemplate.value = template
  dialogOpen.value = true
}

async function deleteTemplate(template: Template) {
  try {
    await ElMessageBox.confirm(`确定要删除模板“${template.name}”吗？`, '删除模板', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    deletingId.value = template.id
    await templateService.deleteTemplate(template.id)
    ElMessage.success('模板删除成功')
    await loadTemplates()
  } catch (error: any) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(error.response?.data?.detail || '删除模板失败')
    }
  } finally {
    deletingId.value = null
  }
}
</script>

<template>
  <section class="templates-view">
    <div class="page-header glass-card">
      <div>
        <h2>模板管理</h2>
        <p>维护测试用例输出字段，系统模板仅支持查看。</p>
      </div>
      <div class="header-actions">
        <el-button :loading="isLoading" @click="loadTemplates">刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="openDialog('create')">创建模板</el-button>
      </div>
    </div>

    <div v-if="isLoading && templates.length === 0" class="glass-card loading-card">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else-if="templates.length === 0" class="glass-card empty-card">
      <el-empty description="暂无模板，请创建一个模板" />
      <el-button type="primary" :icon="Plus" @click="openDialog('create')">创建模板</el-button>
    </div>

    <div v-else class="template-grid">
      <article v-for="template in templates" :key="template.id" class="glass-card template-card">
        <div class="card-header">
          <div>
            <h3>{{ template.name }}</h3>
            <div class="badges">
              <el-tag v-if="template.is_default" type="warning" effect="light">
                <el-icon><Star /></el-icon>
                默认
              </el-tag>
              <el-tag v-if="template.is_system" type="info" effect="plain">系统内置</el-tag>
            </div>
          </div>
          <span class="field-count">{{ template.fields.length }} 个字段</span>
        </div>

        <div class="field-preview">
          <el-tag v-for="field in template.fields.slice(0, 5)" :key="field.name" effect="plain">
            {{ field.name }}
          </el-tag>
          <span v-if="template.fields.length > 5" class="more-fields">
            +{{ template.fields.length - 5 }}
          </span>
        </div>

        <div class="card-actions">
          <el-button
            v-if="template.is_system"
            :icon="View"
            @click="openDialog('view', template)"
          >查看</el-button>
          <template v-else>
            <el-button :icon="Edit" @click="openDialog('edit', template)">编辑</el-button>
            <el-button
              type="danger"
              plain
              :icon="Delete"
              :loading="deletingId === template.id"
              @click="deleteTemplate(template)"
            >删除</el-button>
          </template>
        </div>
      </article>
    </div>

    <TemplateDialog
      v-model="dialogOpen"
      :mode="dialogMode"
      :template="selectedTemplate"
      @saved="loadTemplates"
    />
  </section>
</template>

<style scoped>
.templates-view {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
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

.page-header p {
  margin-top: 6px;
  color: var(--color-text-secondary);
}

.header-actions,
.card-actions,
.badges,
.field-preview {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.loading-card,
.empty-card {
  padding: 32px;
}

.empty-card {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 18px;
}

.template-card {
  min-height: 220px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.template-card:hover { box-shadow: var(--shadow-md); }

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.card-header h3 {
  margin-bottom: 10px;
  font-size: 18px;
}

.field-count,
.more-fields {
  flex: none;
  color: var(--color-text-secondary);
  font-size: 13px;
}

.field-preview {
  min-height: 50px;
  align-content: flex-start;
}

.card-actions {
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid var(--color-border);
  justify-content: flex-end;
}

@media (max-width: 760px) {
  .page-header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>

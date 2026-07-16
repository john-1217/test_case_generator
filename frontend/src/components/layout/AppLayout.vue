<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Collection, Cpu, Document, Files } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import CreateTaskDialog from '../task/CreateTaskDialog.vue'
import { useAuthStore } from '../../stores/auth'
import { useTaskStore } from '../../stores/task'
import AppIcon from '../ui/AppIcon.vue'

const authStore = useAuthStore()
const taskStore = useTaskStore()
const route = useRoute()
const router = useRouter()
const createTaskOpen = ref(false)

const navItems = [
  { path: '/tasks', label: '任务列表', icon: Document },
  { path: '/templates', label: '模板管理', icon: Files },
  { path: '/llm', label: '模型配置', icon: Cpu },
  { path: '/knowledge', label: '知识库', icon: Collection },
]

const showCreateButton = computed(() => route.path === '/tasks')

function logout() {
  authStore.logout()
  router.push('/login')
}

async function handleCreated() {
  createTaskOpen.value = false
  await router.push('/tasks')
  await taskStore.fetchTasks(1)
  ElMessage.success('任务创建成功')
}
</script>

<template>
  <div class="layout-shell">
    <header class="topbar">
      <div class="brand" @click="router.push('/tasks')">
        <div class="brand-icon"><AppIcon :size="26" /></div>
        <div class="brand-copy">
          <h1>Test Case Generator</h1>
          <span>测试用例管理平台</span>
        </div>
      </div>
      <div class="topbar-actions">
        <span class="username">{{ authStore.username }}</span>
        <el-button v-if="showCreateButton" type="primary" @click="createTaskOpen = true">
          新建任务
        </el-button>
        <el-button text @click="logout">退出登录</el-button>
      </div>
    </header>

    <div class="content-shell">
      <aside class="sidebar">
        <nav class="navigation" aria-label="主导航">
          <RouterLink
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            :class="{ active: route.path === item.path }"
          >
            <el-icon :size="18"><component :is="item.icon" /></el-icon>
            <span>{{ item.label }}</span>
          </RouterLink>
        </nav>
      </aside>

      <main class="main-panel">
        <slot />
      </main>
    </div>

    <CreateTaskDialog v-model="createTaskOpen" @created="handleCreated" />
  </div>
</template>

<style scoped>
.layout-shell {
  min-height: 100vh;
  background: var(--color-bg);
}
.topbar {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}
.brand { display: flex; align-items: center; gap: 10px; cursor: pointer; }
.brand-icon {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-md);
  color: white;
  background: var(--color-primary);
}
.brand-copy { display: flex; flex-direction: column; gap: 1px; }
.brand h1 { margin: 0; font-size: 16px; line-height: 1.25; letter-spacing: -0.01em; }
.brand-copy span { color: var(--color-text-muted); font-size: 12px; }
.topbar-actions { display: flex; align-items: center; gap: 12px; }
.username { color: var(--color-text-secondary); font-size: 14px; }
.content-shell {
  display: grid;
  grid-template-columns: 232px minmax(0, 1fr);
  min-height: calc(100vh - 64px);
}
.sidebar {
  padding: 20px 12px;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
}
.navigation { display: flex; flex-direction: column; gap: 4px; }
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 40px;
  padding: 0 12px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  font-size: 14px;
  font-weight: 600;
  transition: background-color 0.18s ease, border-color 0.18s ease, color 0.18s ease;
}
.nav-item:hover { background: #f8fafc; color: var(--color-primary); }
.nav-item.active {
  border-color: #dbeafe;
  background: var(--color-primary-light);
  color: var(--color-primary-dark);
}
.main-panel {
  min-width: 0;
  max-width: 1600px;
  width: 100%;
  margin: 0 auto;
  padding: 28px 32px 40px;
}

@media (max-width: 900px) {
  .topbar { padding: 0 20px; }
  .content-shell { display: block; }
  .sidebar {
    padding: 8px 16px;
    overflow-x: auto;
    border-right: 0;
    border-bottom: 1px solid var(--color-border);
  }
  .navigation { flex-direction: row; min-width: max-content; }
  .nav-item { flex: 0 0 auto; }
  .main-panel { padding: 22px 20px 32px; }
}

@media (max-width: 560px) {
  .topbar { padding: 0 14px; }
  .brand-copy span,
  .username { display: none; }
  .topbar-actions { gap: 4px; }
  .topbar-actions :deep(.el-button) { padding-inline: 8px; }
  .main-panel { padding: 18px 14px 28px; }
}
</style>

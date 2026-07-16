<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
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
  { path: '/tasks', label: '任务列表', icon: '📋' },
  { path: '/templates', label: '模板管理', icon: '📄' },
  { path: '/llm', label: '模型配置', icon: '🤖' },
  { path: '/knowledge', label: '知识库', icon: '🗄️' },
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
    <header class="topbar glass-card">
      <div class="brand" @click="router.push('/tasks')">
        <div class="brand-icon"><AppIcon :size="27" /></div>
        <h1>Test Case Generator</h1>
      </div>
      <div class="topbar-actions">
        <span class="username">{{ authStore.username }}</span>
        <el-button v-if="showCreateButton" type="primary" @click="createTaskOpen = true">
          新建任务
        </el-button>
        <el-button @click="logout">退出</el-button>
      </div>
    </header>

    <div class="content-shell">
      <aside class="sidebar glass-card">
        <RouterLink
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: route.path === item.path }"
        >
          <span>{{ item.icon }}</span>
          {{ item.label }}
        </RouterLink>
      </aside>

      <main class="main-panel">
        <slot />
      </main>
    </div>

    <CreateTaskDialog v-model="createTaskOpen" @created="handleCreated" />
  </div>
</template>

<style scoped>
.layout-shell { min-height: 100vh; padding: 24px; }
.topbar {
  height: 72px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 22px;
}
.brand { display: flex; align-items: center; gap: 12px; cursor: pointer; }
.brand-icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  color: white;
  background: var(--gradient-primary);
  box-shadow: 0 10px 24px rgba(79, 124, 255, 0.28);
}
.brand h1 { font-size: 20px; margin: 0; }
.topbar-actions { display: flex; align-items: center; gap: 12px; }
.username { color: var(--color-text-secondary); }
.content-shell { display: grid; grid-template-columns: 220px minmax(0, 1fr); gap: 22px; }
.sidebar { padding: 14px; height: calc(100vh - 118px); position: sticky; top: 94px; }
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px 14px;
  margin-bottom: 8px;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  transition: all 0.2s ease;
}
.nav-item:hover { background: rgba(79, 124, 255, 0.08); color: var(--color-primary); }
.nav-item.active {
  background: var(--gradient-primary);
  color: white;
  box-shadow: 0 10px 24px rgba(79, 124, 255, 0.24);
}
.main-panel { min-width: 0; }

@media (max-width: 900px) {
  .layout-shell { padding: 14px; }
  .topbar {
    height: auto;
    min-height: 64px;
    padding: 12px 16px;
    margin-bottom: 14px;
  }
  .brand h1 { font-size: 17px; }
  .username { display: none; }
  .content-shell { grid-template-columns: 1fr; gap: 14px; }
  .sidebar {
    position: static;
    height: auto;
    display: flex;
    gap: 6px;
    padding: 8px;
    overflow-x: auto;
  }
  .nav-item {
    flex: 0 0 auto;
    margin: 0;
    white-space: nowrap;
  }
}

@media (max-width: 560px) {
  .brand h1 { display: none; }
  .topbar-actions { gap: 6px; }
  .topbar-actions :deep(.el-button) { padding-inline: 10px; }
}
</style>

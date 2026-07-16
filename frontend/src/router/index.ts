import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import TasksView from '../views/TasksView.vue'
import TemplatesView from '../views/TemplatesView.vue'
import LlmConfigView from '../views/LlmConfigView.vue'
import KnowledgeView from '../views/KnowledgeView.vue'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/tasks' },
    { path: '/login', component: LoginView, meta: { public: true } },
    { path: '/tasks', component: TasksView, meta: { title: '任务列表' } },
    { path: '/templates', component: TemplatesView, meta: { title: '模板管理' } },
    { path: '/llm', component: LlmConfigView, meta: { title: '模型配置' } },
    { path: '/knowledge', component: KnowledgeView, meta: { title: '知识库' } },
  ],
})

router.beforeEach((to) => {
  const authStore = useAuthStore()
  authStore.init()

  if (!to.meta.public && !authStore.isAuthenticated) {
    return '/login'
  }

  if (to.path === '/login' && authStore.isAuthenticated) {
    return '/tasks'
  }
})

export default router

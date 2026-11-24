# 03 — 前端结构（frontend/）

Vue 3 + TypeScript + Vite + Element Plus + Pinia + Vue Router 的 SPA，所有数据经 Axios 调用后端 `/api/v1`。

## 1. 技术栈与构建

- **[package.json](../../frontend/package.json)**：
  - scripts：`dev`（Vite 开发服务器 :5174）、`build`（`vue-tsc -b && vite build`）、`preview`
  - dependencies：`vue@3.5`、`vue-router@4`、`pinia`、`element-plus` + `@element-plus/icons-vue`、`axios`、`marked`（Markdown 渲染）、`dompurify`（XSS 过滤）
  - devDependencies：`typescript`、`vite`、`@vitejs/plugin-vue`、`vue-tsc`
- **[vite.config.ts](../../frontend/vite.config.ts)**：开发模式将 `/api` 代理到 `http://localhost:8080`。
- **[main.ts](../../frontend/src/main.ts)**：`createApp` → `createPinia()` → ElementPlus → `router`。
- **[App.vue](../../frontend/src/App.vue)**：`meta.public` 路由（登录页）直接渲染，其余路由统一包裹 [AppLayout](../../frontend/src/components/layout/AppLayout.vue)。

## 2. 路由与守卫 — [router/index.ts](../../frontend/src/router/index.ts)

| 路径 | 视图 | 说明 |
| --- | --- | --- |
| `/` | — | 重定向 `/tasks` |
| `/login` | [LoginView.vue](../../frontend/src/views/LoginView.vue) | `meta.public` |
| `/tasks` | [TasksView.vue](../../frontend/src/views/TasksView.vue) | 任务列表（首页） |
| `/templates` | [TemplatesView.vue](../../frontend/src/views/TemplatesView.vue) | 用例模板管理 |
| `/llm` | [LlmConfigView.vue](../../frontend/src/views/LlmConfigView.vue) | 模型配置 |
| `/knowledge` | [KnowledgeView.vue](../../frontend/src/views/KnowledgeView.vue) | 知识库管理 |

守卫 `beforeEach`（L21-L32）：每次导航先 `authStore.init()` 从 localStorage 恢复登录态；未登录访问受保护路由 → `/login`；已登录访问 `/login` → `/tasks`。

## 3. 状态管理（Pinia stores）

### [stores/auth.ts](../../frontend/src/stores/auth.ts)

- state：`token` / `username` / `isAuthenticated`
- actions：`init()`（localStorage 恢复）、`login(username, password)`（调 `authService.login` 并持久化 token）、`logout()`（清空 + 跳登录页）

### [stores/task.ts](../../frontend/src/stores/task.ts)

- state：`tasks` / `total` / `page` / `pageSize` / `isLoading`
- actions：`fetchTasks()`（分页拉取）、`deleteTask(id)`、`stopTask(id)`、`clarifyTask(id, input)` 等，是任务模块状态中枢。

## 4. API 封装 — [services/api.ts](../../frontend/src/services/api.ts)

Axios 实例：`baseURL: '/api/v1'`、timeout 30s（知识库上传单独 120s）；请求拦截器从 localStorage 注入 `Authorization: Bearer <token>`；响应拦截器捕获 401 → 清除登录态并跳 `/login`。

Service 方法清单：

| Service | 方法 |
| --- | --- |
| `authService` | `login` |
| `taskService` | `getTasks` / `uploadFile` / `createTask` / `clarifyTask` / `stopTask` / `deleteTask` / `getSummary` / `getDownloadUrl` / `downloadFile`（Blob 下载并解析 Content-Disposition 文件名） |
| `templateService` | `getTemplates` / `createTemplate` / `updateTemplate` / `deleteTemplate` |
| `llmConfigService` | `getModelGroups` / `getProviderList` / `getProviderConfig` / `saveProviderConfig` / `fetchModels` / `addModel` / `deleteModel` / `testModel` |
| `knowledgeService` | `getEmbeddingProviders` / `getProjects` / `getProject` / `createProject` / `updateProject` / `deleteProject` / `getDocuments` / `uploadDocument` / `deleteDocument` / `search` |

类型定义集中在 [services/types.ts](../../frontend/src/services/types.ts)：核心类型 `Task`（task_id、original_filename、status、current_step、clarification_message、summary_content、error_message、时间戳等）、`Template`、`ProviderConfig`、`ModelGroup`、`Project`、`KnowledgeDocument`、`KnowledgeSearchResult`、`EmbeddingProviderInfo` 等，与后端 schema 一一对应。

## 5. 组合式函数

### [composables/useTaskPolling.ts](../../frontend/src/composables/useTaskPolling.ts)

默认每 5 秒调用 `taskStore.fetchTasks()` 刷新任务列表，供 TasksView 使用，实现运行中任务的进度/状态实时更新。

## 6. 视图

| 视图 | 主要交互 |
| --- | --- |
| [LoginView.vue](../../frontend/src/views/LoginView.vue) | 表单登录，成功后跳 `/tasks` |
| [TasksView.vue](../../frontend/src/views/TasksView.vue) | 使用 `useTaskPolling()`；维护 `selectedTaskId` 与三个对话框开关（澄清/进度/总结），点击对应操作时加载总结内容并打开 Dialog；通过 AppLayout 的「新建任务」入口创建任务 |
| [TemplatesView.vue](../../frontend/src/views/TemplatesView.vue) | 模板列表 + TemplateDialog 增改 |
| [LlmConfigView.vue](../../frontend/src/views/LlmConfigView.vue) | 厂商配置（base_url/api_key）、拉取/添加/删除模型、连接测试 |
| [KnowledgeView.vue](../../frontend/src/views/KnowledgeView.vue) | 项目切换 → 加载文档列表；存在 `processing` 文档时启动轮询（L59-L96），完成后刷新项目列表；上传/删除文档（L136-L171） |

## 7. 组件

### layout

- [AppLayout.vue](../../frontend/src/components/layout/AppLayout.vue)：顶部导航（任务/模板/模型配置/知识库）+ 登出；`/tasks` 页显示「新建任务」按钮，内嵌 CreateTaskDialog，创建成功后刷新列表。

### task/（任务模块 5 个组件）

| 组件 | 职责 |
| --- | --- |
| [TaskTable.vue](../../frontend/src/components/task/TaskTable.vue) | 任务表格；props `tasks/isLoading`，emits `refresh/clarify/progress/summary`；内部实现停止、下载、删除（L41-L80）；按状态渲染操作按钮：RUNNING→进度/停止，CLARIFYING→补充说明，FINISHED→下载/总结/删除（L105-L155） |
| [CreateTaskDialog.vue](../../frontend/src/components/task/CreateTaskDialog.vue) | 打开时并行加载模板、模型分组、知识库项目并恢复上次模型选择（L51-L79）；提交时校验模型/文件/输出文件名，先 `/upload` 再 `createTask`（L91-L129），成功后 emit `created` |
| [ClarificationDialog.vue](../../frontend/src/components/task/ClarificationDialog.vue) | 展示待澄清问题，提交澄清信息 / 忽略继续 / 停止生成 |
| [ProgressDialog.vue](../../frontend/src/components/task/ProgressDialog.vue) | 按 `current_step` 可视化工作流进度 |
| [SummaryDialog.vue](../../frontend/src/components/task/SummaryDialog.vue) | Markdown 渲染测试覆盖总结（marked + DOMPurify） |

### knowledge/

| 组件 | 职责 |
| --- | --- |
| [ProjectDialog.vue](../../frontend/src/components/knowledge/ProjectDialog.vue) | 创建/编辑知识库项目（名称、描述、Embedding provider 与模型选择） |
| [DocumentList.vue](../../frontend/src/components/knowledge/DocumentList.vue) | 文档列表；props `documents/loading/uploading`，emits `upload/refresh/delete`；将 processing/ready/failed 映射为状态标签（L29-L49），隐藏 input 触发文件选择上传 |

### template/

- [TemplateDialog.vue](../../frontend/src/components/template/TemplateDialog.vue)：模板字段的动态编辑（字段名 + 描述列表的增删改）。

### ui/

- [AppIcon.vue](../../frontend/src/components/ui/AppIcon.vue)：图标封装。
- [StatusBadge.vue](../../frontend/src/components/ui/StatusBadge.vue)：任务状态徽标（状态 → 颜色/文案映射）。

## 8. 前端任务交互时序（典型）

```text
AppLayout「新建任务」→ CreateTaskDialog（选模型/模板/知识库 + 上传文档）
  → created → TasksView 刷新 → useTaskPolling 每 5s 轮询
  → RUNNING：ProgressDialog 展示 current_step；可停止
  → CLARIFYING：ClarificationDialog 提交澄清 → clarifyTask → 恢复轮询
  → FINISHED：下载 Excel（downloadFile）或查看 SummaryDialog
```

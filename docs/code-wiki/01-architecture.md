# 01 — 项目整体架构

## 1. 架构总览

```text
┌─────────────────────────────┐
│  Vue 3 + Vite SPA (TS)      │  Element Plus UI
│  views / components / stores│
└──────────────┬──────────────┘
               │  HTTP /api/v1（Bearer JWT）
               ▼
┌─────────────────────────────────────────────────────────┐
│  FastAPI 后端（backend/app）                              │
│  ┌───────────┐  ┌──────────────────────────────────────┐│
│  │ api/ 路由层 │→│ services/ 业务层                       ││
│  │ auth      │  │  DocumentParser（PyMuPDF/python-docx）││
│  │ task      │  │  CaseGeneratorWorkflow（LangGraph）   ││
│  │ template  │  │  KnowledgeBaseService（ChromaDB RAG） ││
│  │ llm_config│  │  EmbeddingService / LlmService       ││
│  │ knowledge │  │  ResultExtractor（Markdown→Excel）    ││
│  └───────────┘  └──────────────────────────────────────┘│
│        │                    │              │            │
│        ▼                    ▼              ▼            │
│  SQLite（aiosqlite）   ChromaDB 向量库   各厂商 LLM API   │
└─────────────────────────────────────────────────────────┘
```

- **前端**：Vue 3 SPA，仅调用 `/api/v1` 下的 REST 接口；开发模式由 Vite 代理 `/api` 到后端 8080，生产模式由 FastAPI 托管构建产物（见 [main.py](../../backend/app/main.py) 中 `SPAStaticFiles`）。
- **后端**：单体 FastAPI 应用，路由层（`app/api/`）+ 业务服务层（`app/services/`）+ ORM 模型层（`app/models/`），SQLite 持久化业务数据，ChromaDB 持久化知识库向量。
- **LLM**：通过 LangChain 接入 OpenAI / Gemini / Anthropic / DeepSeek / Kimi / OpenRouter 六个厂商（配置见 [llm_config.py 模型](../../backend/app/models/llm_config.py)）。

## 2. 分层与职责

| 层 | 目录 | 职责 |
| --- | --- | --- |
| 应用入口 | [backend/app/main.py](../../backend/app/main.py) | lifespan 中初始化数据库（含系统默认模板），注册 `/api/v1` 路由、`/health`、SPA 静态托管 |
| 路由层 | [backend/app/api/](../../backend/app/api/__init__.py) | HTTP 端点、参数校验（Pydantic schema）、编排后台任务 |
| 服务层 | [backend/app/services/](../../backend/app/services/__init__.py) | 文档解析、LangGraph 工作流、RAG 检索、Embedding、LLM 连接测试、结果提取 |
| 模型层 | [backend/app/models/](../../backend/app/models/__init__.py) | SQLAlchemy ORM：Task / CaseTemplate / ProviderConfig(+ProviderModel) / Project(+KnowledgeDocument) |
| Schema 层 | [backend/app/schemas/](../../backend/app/schemas/__init__.py) | 请求/响应 Pydantic 模型 |
| 基础设施 | [backend/app/core/](../../backend/app/core/config.py) | Settings 配置、异步 SQLAlchemy 引擎、JWT/bcrypt 安全 |

## 3. 核心数据流一：测试用例生成任务

入口：前端「新建任务」→ [task.py `create_task`](../../backend/app/api/task.py#L69-L123) → 后台任务 [`_run_workflow`](../../backend/app/api/task.py#L155-L263)。

```text
上传文档(/upload) → 创建任务(/task/create, status=RUNNING)
  → 后台 _run_workflow:
      ① doc_parsing      DocumentParser 解析文档（线程池执行）→ 保存 <task_id>_parsed_document.md
      ② rag_retrieval    （可选）关联知识库项目时 _retrieve_rag_context()
      ③ phase1_analysis  LangGraph 节点：需求分析 + 澄清问题识别
      ④ phase2_strategy  测试策略与覆盖设计
      ⑤ phase3_generate  生成 Markdown 测试用例表格（可被自定义模板覆盖）
      ⑥ phase4_summary   测试覆盖度总结
      ⑦ extracting       ResultExtractor：完整报告 MD + 总结 MD + Excel
  → status=FINISHED / CLARIFYING / FAILED
```

任务进度通过模块级内存字典维护（[task.py L33-L37](../../backend/app/api/task.py#L33-L37)）：

- `_workflows: dict[thread_id, CaseGeneratorWorkflow]` — 澄清恢复所需的工作流实例（含 InMemorySaver checkpointer）
- `_task_progress: dict[task_id, step]` — 当前步骤，供 `/tasks` 轮询展示
- `_cancelled_tasks: set[task_id]` — 取消标记，`on_step` 回调在下一检查点抛出 `TaskCancelledException`

> **限制**：澄清恢复依赖同进程内存状态，后端重启后处于 `CLARIFYING` 的任务无法恢复（`_resume_workflow` 会报「工作流实例丢失」）。

## 4. 核心数据流二：LangGraph 四阶段工作流

定义：[`CaseGeneratorWorkflow._build_graph`](../../backend/app/services/case_generator.py#L153-L191)，状态为 [`WorkflowState`](../../backend/app/services/case_generator.py#L104-L121)。

```text
START → phase1_analysis ─┬─ has_clarification → human_clarification(interrupt) → phase2_strategy
                         └─ 否则 ─────────────────────────────────────────────→ phase2_strategy
phase2_strategy → phase3_generate → phase4_summary → END
（human_clarification 中输入「停止生成」→ is_stopped → END）
```

- **Prompt 装配**：[`load_phase_prompt`](../../backend/app/services/case_generator.py#L23-L41) 将 `config/prompts/role.md` 与对应阶段 prompt 拼接为 System Message。
- **多模态输入**：[`_build_document_content`](../../backend/app/services/case_generator.py#L217-L258) 组装 RAG 上下文 + 文档正文 + 表格 + Base64 图片。
- **澄清机制**：Phase 1 输出中出现标记「无法继续生成测试用例，存在以下问题需要澄清」则置 `has_clarification`；`human_clarification` 节点用 LangGraph `interrupt()` 挂起，用户经 `/task/{id}/clarify` 提交后以 `Command(resume=...)` 恢复（见 [`resume`](../../backend/app/services/case_generator.py#L547-L551)）。
- **模板覆盖**：自定义模板只影响 Phase 3 输出格式，[`_build_prompt_with_template`](../../backend/app/api/task.py#L534-L562) 用正则替换 `phase3_generate.md` 的 3.3 节字段定义。
- **可观测性**：[`get_trace_config`](../../backend/app/services/case_generator.py#L193-L213) 为每次调用生成 thread_id / tags / metadata，配合 LangSmith tracing（默认关闭）。

## 5. 核心数据流三：知识库 RAG 检索

入库：上传知识文档 → 后台解析 + 表格感知分块（[`KnowledgeBaseService._split_with_table_awareness`](../../backend/app/services/knowledge_service.py#L50-L125)）→ Embedding → 写入 ChromaDB collection `project_<id>`。

检索（[`_retrieve_rag_context`](../../backend/app/api/task.py#L565-L701)）：

```text
需求文档 → 轻量 LLM 提取 ≤10 个功能模块主题（每厂商配轻量模型，见 _LITE_MODELS）
        → 按主题逐个向量检索 ChromaDB（每主题 top-3）
        → 按 chunk 内容 hash 去重 → 拼接为 RAG context
        → 注入 Phase 1 输入（置于需求文档之前，提供全局背景）
```

Embedding 支持：本地 HuggingFace `BAAI/bge-small-zh-v1.5`（无需 API Key，不自动下载）与 OpenAI / Gemini / OpenRouter 远程模型（见 [embedding_service.py](../../backend/app/services/embedding_service.py)）。

## 6. 任务状态机

`TaskStatus`（[models/task.py](../../backend/app/models/task.py#L10-L14)）：

```text
RUNNING(0) ──Phase1 要求澄清──→ CLARIFYING(1) ──提交澄清──→ RUNNING(0) ──→ FINISHED(2)
    │                              │
    │ 用户停止/异常/实例丢失          │ 停止生成 / 忽略继续
    ▼                              ▼
 FAILED(3) ◄──────────────────────┘
```

`current_step` 取值序列：`doc_parsing → rag_retrieval → phase1_analysis → phase2_strategy → phase3_generate → phase4_summary → extracting`。

## 7. 前后端契约

前端 [services/api.ts](../../frontend/src/services/api.ts) 通过 Axios 实例（baseURL `/api/v1`，请求拦截器注入 Bearer token，401 时登出跳转）调用后端；完整端点对照见 [02-backend.md](./02-backend.md#3-api-端点清单) 与 [03-frontend.md](./03-frontend.md)。

认证：仅环境变量配置的管理员账号（[`auth.py`](../../backend/app/api/auth.py)），JWT（python-jose + bcrypt），无注册流程。

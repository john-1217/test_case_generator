# 05 — 依赖关系

## 1. 后端依赖 — [backend/pyproject.toml](../../backend/pyproject.toml)

Python ≥ 3.11，包管理使用 [uv](https://docs.astral.sh/uv/)，构建后端 hatchling。

### 运行时依赖及用途

| 依赖 | 版本约束 | 用途 |
| --- | --- | --- |
| fastapi | ≥0.115 | Web 框架（路由、BackgroundTasks、依赖注入） |
| uvicorn[standard] | ≥0.32 | ASGI 服务器 |
| python-multipart | ≥0.0.12 | 文件上传（multipart/form-data） |
| sqlalchemy | ≥2.0 | ORM（Mapped / mapped_column 新式声明） |
| aiosqlite | ≥0.20 | SQLite 异步驱动 |
| python-jose[cryptography] | ≥3.3 | JWT 签发与校验 |
| passlib[bcrypt] | ≥1.7.4 | 密码哈希（实际代码直接使用 bcrypt） |
| langgraph / langgraph-checkpoint | ≥0.2 / ≥2.0 | 工作流状态图 + `InMemorySaver` checkpointer + `interrupt/Command` |
| langchain / langchain-core | ≥0.3 | LLM 消息抽象与基础接口 |
| langchain-openai | ≥0.2 | `ChatOpenAI`（openai/deepseek/kimi 及兼容模式）、`OpenAIEmbeddings` |
| pandas / openpyxl | ≥2.0 / ≥3.1 | 用例表格 DataFrame 处理与 Excel 导出 |
| pydantic / pydantic-settings | ≥2.0 | Schema 校验与环境配置 |
| python-dotenv | ≥1.0 | `.env` 加载 |
| greenlet | ≥3.3 | SQLAlchemy 异步协程支撑 |
| chromadb | ≥0.5 | 知识库向量存储（持久化客户端） |
| langchain-text-splitters | ≥0.3 | 知识库文档分块 |
| pymupdf | ≥1.24 | PDF 解析（文本/表格/图片，无 OCR） |
| python-docx | ≥1.1 | DOCX 解析 |
| sentence-transformers | ≥3.0 | 本地 HuggingFace Embedding（BGE 模型） |

### 可选（未声明，运行时按需导入）

| 依赖 | 触发条件 | 缺失时行为 |
| --- | --- | --- |
| `langchain-google-genai` | provider=gemini 且走原生集成 | 回退 OpenAI 兼容模式（见 [case_generator.py L70-L83](../../backend/app/services/case_generator.py#L70-L83)） |
| `langchain-anthropic` | provider=anthropic | 抛 `ImportError`（[case_generator.py L86-L94](../../backend/app/services/case_generator.py#L86-L94)） |

### 开发依赖

- pytest ≥8.0、pytest-asyncio ≥0.24（`[dependency-groups] dev`）

## 2. 前端依赖 — [frontend/package.json](../../frontend/package.json)

Node ≥ 20，构建工具 Vite 8 + TypeScript 6 + vue-tsc。

| 依赖 | 用途 |
| --- | --- |
| vue@^3.5 / vue-router@^4.6 / pinia | SPA 框架、路由、状态管理 |
| element-plus@^2.14 + @element-plus/icons-vue | UI 组件库与图标 |
| axios@^1.18 | HTTP 客户端 |
| marked@^18 | Markdown 渲染（任务总结） |
| dompurify@^3.4 | Markdown 渲染前的 XSS 过滤 |
| vite / @vitejs/plugin-vue / typescript / vue-tsc / @types/* | 构建与类型检查（devDependencies） |

## 3. 后端模块内部依赖关系

```text
main.py
 ├── core.config (get_settings)
 ├── core.database (init_db → models 全量注册)
 ├── core.config.configure_langsmith_tracing
 └── api.router
      ├── auth.py ──────────→ core.security, core.config
      ├── task.py ──────────→ services.{DocumentParser, CaseGeneratorWorkflow, ResultExtractor,
      │                        KnowledgeBaseService, embedding_service}
      │                        models.{Task, CaseTemplate, ProviderConfig, Project}
      │                        core.database(AsyncSessionLocal)
      │                        case_generator.create_llm（RAG 主题提取）
      ├── template.py ──────→ models.CaseTemplate
      ├── llm_config.py ────→ models.{ProviderConfig, ProviderModel}, services.llm_service,
      │                        models.llm_config.PROVIDER_DEFAULTS/ORDER
      └── knowledge.py ─────→ models.{Project, KnowledgeDocument},
                               services.{KnowledgeBaseService, embedding_service}

services.case_generator ──→ core.config, services.document_parser(ParsedDocument),
                            langgraph.*, langchain_openai, config/prompts/*.md
services.knowledge_service → chromadb, langchain_text_splitters, embedding_service(注入 embeddings)
services.embedding_service → sentence_transformers, langchain_openai(OpenAIEmbeddings), core.config
services.document_parser ──→ pymupdf, python_docx
services.result_extractor ─→ pandas, openpyxl
services.llm_service ─────→ httpx（纯 HTTP，无 LangChain）
```

关键耦合点：

- **API 层持有业务状态**：`task.py` 的 `_workflows` / `_task_progress` / `_cancelled_tasks` 是进程内存态，多 worker / 重启会丢失（详见 [01-architecture.md §3](./01-architecture.md#3-核心数据流一测试用例生成任务)）。
- **Embeddings 显式传递**：`KnowledgeBaseService.search/add_document` 不自行创建 Embedding，由调用方（knowledge API / task RAG）构造后传入，保证入库与查询使用同一模型。
- **Prompt 与代码耦合**：`_build_prompt_with_template` 依赖 `phase3_generate.md` 中「### 3.3 测试用例输出格式」与「**特殊说明：**」的固定标题结构。

## 4. 外部服务依赖

| 外部服务 | 使用位置 | 说明 |
| --- | --- | --- |
| LLM API（OpenAI/Gemini/Anthropic/DeepSeek/Kimi/OpenRouter） | case_generator（生成）、llm_service（测试）、task RAG 主题提取 | 用户在「模型配置」页填写 base_url + api_key |
| Embedding API（OpenAI/Gemini/OpenRouter） | 知识库入库与检索 | 复用 ProviderConfig；本地模型则无需 |
| HuggingFace 本地模型 `BAAI/bge-small-zh-v1.5` | embedding_service | 路径由 `LOCAL_EMBEDDING_MODEL_PATH` 提供，仅本地文件，不自动下载 |
| LangSmith | case_generator（trace config） | 默认关闭，需 `LANGSMITH_TRACING=true` + API Key |

## 5. Provider 支持矩阵

| Provider | Chat 生成 | 原生 SDK | 缺 SDK 回退 | Embedding | RAG 轻量模型 |
| --- | --- | --- | --- | --- | --- |
| openai | ✅ | langchain-openai | — | ✅ | gpt-4o-mini |
| deepseek | ✅ | langchain-openai（兼容） | — | ❌ | deepseek-chat |
| kimi | ✅ | langchain-openai（兼容） | — | ❌ | moonshot-v1-8k |
| gemini | ✅ | langchain-google-genai（可选） | OpenAI 兼容 | ✅ | gemini-2.0-flash-lite |
| anthropic | ✅ | langchain-anthropic（可选） | 无（报错） | ❌ | claude-3-haiku |
| openrouter | ✅ | langchain-openai（兼容） | — | ✅ | google/gemini-2.0-flash-lite |
| local_huggingface | ❌ | sentence-transformers | — | ✅（默认 BGE 中文小模型） | — |

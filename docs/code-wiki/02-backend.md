# 02 — 后端模块职责

后端代码位于 [backend/app/](../../backend/app/main.py)，按「入口 → core → api → services → models/schemas」分层。

## 1. 应用入口与基础设施

### main.py — [backend/app/main.py](../../backend/app/main.py)

| 符号 | 行号 | 说明 |
| --- | --- | --- |
| `lifespan(app)` | L18 | 启动时调用 `init_db()` 建表并初始化系统默认模板，配置 LangSmith tracing |
| `health_check()` | L44 | `GET /health` 健康检查 |
| `SPAStaticFiles` | L48 | 静态文件类，对未知路径回退 `index.html`（支持 Vue history 路由刷新），挂载于 `/app/static`（Docker 内含前端产物时） |

### core/ — 基础设施

- **[config.py](../../backend/app/core/config.py)**：`Settings`（pydantic-settings，读 `.env`）定义全部配置项：`database_url` / `upload_dir` / `output_dir` / `chroma_dir` / `max_file_size` / `jwt_*` / `local_embedding_*` / `langsmith_*` / `admin_username` / `admin_password` / `demo_mode`。`get_settings()`（L92）带缓存；`configure_langsmith_tracing()`（L66）将配置映射为 LangSmith 环境变量。
- **[database.py](../../backend/app/core/database.py)**：异步 SQLAlchemy 引擎（aiosqlite + SQLite），导入时自动创建 data/uploads/outputs/chroma 目录；`get_db()` 会话依赖；`init_db()`（L40）执行 `Base.metadata.create_all` 并调用 `_init_default_template()`（L49）插入「标准测试用例模板」（9 个字段：用例名称、所属模块、标签、前置条件、步骤描述、预期结果、编辑模式、备注、用例等级）。**无迁移框架，改模型需删库重建。**
- **[security.py](../../backend/app/core/security.py)**：`hash_password` / `verify_password`（bcrypt）、`create_access_token` / `decode_token`（python-jose JWT，HS256，默认 24h）。`decode_token` 失败抛 401。

## 2. API 路由层（backend/app/api/）

[api/__init__.py](../../backend/app/api/__init__.py) 将各 router 挂载到 `APIRouter(prefix="/api/v1")`：

| Router | prefix | 职责 |
| --- | --- | --- |
| [auth.py](../../backend/app/api/auth.py) | `/auth` | 管理员登录，签发 JWT |
| [task.py](../../backend/app/api/task.py) | — | 任务全生命周期 + 文件上传/下载 |
| [template.py](../../backend/app/api/template.py) | `/templates` | 用例输出模板 CRUD |
| [llm_config.py](../../backend/app/api/llm_config.py) | `/llm-configs` | 厂商 API 配置、模型管理、连接测试 |
| [knowledge.py](../../backend/app/api/knowledge.py) | `/knowledge` | 知识库项目/文档管理与向量检索 |

### 3. API 端点清单

#### auth

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/auth/login` | 校验环境变量中的管理员账号，返回 `{token, username}` |

#### task（task.py）

| 方法 | 路径 | 行号 | 说明 |
| --- | --- | --- | --- |
| POST | `/upload` | L45 | 上传需求文档（pdf/doc/docx/txt/md，≤50MB），UUID 重命名，返回 `{file_path, original_filename}` |
| POST | `/task/create` | L69 | 校验厂商配置与模板，创建 Task（RUNNING），投递后台 `_run_workflow` |
| POST | `/task/{id}/stop` | L284 | 停止任务：CLARIFYING 直接置 FAILED；RUNNING 加取消标记，下一检查点中断 |
| POST | `/task/{id}/clarify` | L315 | 提交澄清信息；输入「停止生成」则置 FAILED；否则投递后台 `_resume_workflow` |
| GET | `/tasks` | L408 | 分页任务列表（含 `current_step` 与总结内容） |
| DELETE | `/tasks/{id}` | L428 | 删除任务（RUNNING/CLARIFYING 不可删），清理文件与工作流实例 |
| GET | `/download/{task_id}` | L465 | 下载 Excel（仅 FINISHED 且有输出） |
| GET | `/task/{task_id}/summary` | L490 | 读取总结 Markdown 内容 |

#### template（template.py）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/templates` | 模板列表 |
| POST | `/templates` | 创建模板（`fields: [{name, description}]`） |
| PUT | `/templates` | 更新模板（系统模板不可改） |
| DELETE | `/templates/{template_id}` | 删除模板（系统模板不可删） |

#### llm_config（llm_config.py）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/provider-list` | 六厂商列表（含默认 base_url 与预置模型） |
| GET | `/provider-configs/{provider}` | 单厂商配置（API Key 脱敏） |
| PUT | `/provider-configs/{provider}` | 保存 base_url / api_key |
| POST | `/provider-configs/{provider}/models/{model}/test` | 连接测试（调用 chat 接口） |
| POST | `/provider-configs/{provider}/fetch-models` | 拉取远端模型列表 |
| POST | `/provider-configs/{provider}/models` | 手动添加自定义模型 |
| DELETE | `/provider-configs/{provider}/models/{model}` | 删除模型 |
| GET | `/model-groups` | 任务创建页用的「已配置厂商 + 模型」分组 |

#### knowledge（knowledge.py）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/embedding-providers` | 可用 Embedding provider 列表（含本地模型状态） |
| POST/GET | `/projects`、`/projects/{id}`、PUT/DELETE `/projects/{id}` | 知识库项目 CRUD |
| POST | `/projects/{project_id}/documents` | 上传知识文档（后台解析入库） |
| GET | `/projects/{project_id}/documents` | 文档列表（processing/ready/failed） |
| DELETE | `/documents/{doc_id}` | 删除文档（同时清理向量） |
| POST | `/projects/{project_id}/search` | 向量检索（调试/预览用） |

## 4. 服务层（backend/app/services/）

| 服务 | 文件 | 职责 |
| --- | --- | --- |
| `CaseGeneratorWorkflow` | [case_generator.py](../../backend/app/services/case_generator.py) | LangGraph 四阶段工作流 + LLM 工厂 `create_llm` + prompt 加载；详见 [04-key-code.md](./04-key-code.md#1-casegeneratorworkflow) |
| `DocumentParser` | [document_parser.py](../../backend/app/services/document_parser.py) | PDF（PyMuPDF：文本+表格+图片，无 OCR）/ DOCX（python-docx）/ TXT/MD 解析，产出 `ParsedDocument(markdown, tables, images)` |
| `KnowledgeBaseService` | [knowledge_service.py](../../backend/app/services/knowledge_service.py) | ChromaDB 持久客户端、表格感知分块、文档入库/删除、向量检索、collection 统计 |
| Embedding | [embedding_service.py](../../backend/app/services/embedding_service.py) | `create_embeddings()` 工厂：local_huggingface / openai / gemini / openrouter；`LocalHuggingFaceEmbeddings` 加载本地 BGE 模型 |
| `LlmService` 函数组 | [llm_service.py](../../backend/app/services/llm_service.py) | 纯 HTTP 连接测试 `test_connection` 与 `fetch_models`（不依赖 LangChain），按厂商拼 URL/Header/Payload |
| `ResultExtractor` | [result_extractor.py](../../backend/app/services/result_extractor.py) | 从最终报告提取完整 MD、Markdown 表格→DataFrame→Excel、覆盖总结 MD |

## 5. 数据模型（backend/app/models/）

### Task — [models/task.py](../../backend/app/models/task.py)

`TaskStatus`（IntEnum）：`RUNNING=0` / `CLARIFYING=1` / `FINISHED=2` / `FAILED=3`。

`Task` 表 `task`：`id`、`original_filename`、`local_file_path`、`status`、`thread_id`（LangGraph 线程 ID）、`output_excel`、`output_summary`、`download_filename`、`clarification_message`、`error_message`、`finished_at`、`created_at/updated_at`。

### CaseTemplate — [models/case_template.py](../../backend/app/models/case_template.py)

`id`、`name`、`fields`（JSON：`[{name, description}]`）、`is_default`、`is_system`、时间戳。

### ProviderConfig / ProviderModel — [models/llm_config.py](../../backend/app/models/llm_config.py)

- `LLMProvider` 常量类：openai / gemini / anthropic / deepseek / kimi / openrouter。
- `PROVIDER_DEFAULTS`（L20）：每厂商默认 base_url 与预置模型列表；`PROVIDER_ORDER`（L54）控制展示排序。
- `ProviderConfig` 表 `provider_config`：`provider`、`base_url`（仅 host）、`api_key`、`is_available`，一对多 `models`。
- `ProviderModel` 表 `provider_model`：`model_name`、`is_custom`，级联删除。

### Project / KnowledgeDocument — [models/knowledge.py](../../backend/app/models/knowledge.py)

- `Project` 表 `project`：`name`（唯一）、`description`、`embedding_provider`、`embedding_model`、`doc_count`，一对多 documents。每个项目对应一个 ChromaDB collection `project_<id>`。
- `KnowledgeDocument` 表 `knowledge_document`：`project_id`、`original_filename`、`local_file_path`、`file_size`、`chunk_count`、`status`（processing/ready/failed）、`error_message`。

## 6. Schemas（backend/app/schemas/）

请求/响应 Pydantic 模型，与 ORM 解耦：

- [schemas/task.py](../../backend/app/schemas/task.py)：`TokenResponse`、`TaskCreate`（file_path、original_filename、download_filename、template_id、provider、model、project_id）、`TaskClarify`（clarification_input）、`TaskResponse`（含 current_step、summary_content、clarification_message）、`TaskListResponse`。
- [schemas/template.py](../../backend/app/schemas/template.py)：`TemplateField`、`TemplateCreate/Update/Response`。
- [schemas/llm_config.py](../../backend/app/schemas/llm_config.py)：`ProviderConfigUpdate/Response`、`ProviderListItem`、`TestConnectionRequest/Response`、`FetchModelsRequest` 等。
- [schemas/knowledge.py](../../backend/app/schemas/knowledge.py)：`ProjectCreate/Update/Response`、`KnowledgeDocumentResponse`、`KnowledgeSearchRequest/Result/Response`、`EmbeddingProviderInfo`。

## 7. Prompt 配置（backend/config/prompts/）

| 文件 | 用途 |
| --- | --- |
| `role.md` | 角色定义，与每个阶段 prompt 拼接 |
| `phase1_analysis.md` | 步骤0 文档结构识别 + 步骤1 需求分析/澄清 + 步骤1.5 模块对称性检查 |
| `phase2_strategy.md` | 步骤2 测试策略 + 步骤2.5 业务流程闭环验证 + 步骤2.9 自检 |
| `phase3_generate.md` | 步骤3 生成测试用例 Markdown 表格（3.3 节为可被模板替换的输出格式） |
| `phase4_summary.md` | 步骤4 测试覆盖度总结 |

## 8. 测试

[backend/tests/](../../backend/tests/test_langsmith_tracing.py) 目前仅含 LangSmith tracing 相关测试。运行：`cd backend && uv run pytest`。

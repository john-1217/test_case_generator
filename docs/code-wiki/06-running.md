# 06 — 运行方式

## 1. 环境要求

- Python ≥ 3.11（Docker 镜像使用 3.13）
- Node.js ≥ 20（本地前端开发需要；Docker 部署不需要）
- [uv](https://docs.astral.sh/uv/)（Python 包管理）
- Docker + Docker Compose（仅容器化部署需要）

## 2. 本地开发

### 2.1 启动后端

```bash
cd backend
uv sync                       # 安装依赖（含 dev 组 pytest）
cp .env.example .env          # 首次运行复制配置，按需修改
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

启动后可用地址：

| 地址 | 说明 |
| --- | --- |
| http://localhost:8080 | API 根 |
| http://localhost:8080/docs | OpenAPI/Swagger 文档 |
| http://localhost:8080/health | 健康检查 |

### 2.2 启动前端（另开终端）

```bash
cd frontend
npm install
npm run dev        # http://localhost:5174，Vite 将 /api 代理到 http://localhost:8080
```

其他脚本：`npm run build`（vue-tsc 类型检查 + 生产构建）、`npm run preview`（预览构建产物）。

### 2.3 运行测试

```bash
cd backend && uv run pytest            # 全部
cd backend && uv run pytest tests/test_langsmith_tracing.py  # 单文件
```

> 注意：无 LLM API Key 时无法真实跑通用例生成；需先在「模型配置」页配置至少一个厂商。

## 3. Docker 部署

### 3.1 构建本地镜像

```bash
docker build -t test-case-generator .
```

[Dockerfile](../../Dockerfile) 为三阶段构建：① node:20-alpine 构建前端产物 → ② python:3.13-slim + uv 安装后端依赖（`--no-dev`，并做体积清理）→ ③ 最终镜像合并前端静态文件（`/app/static`）与后端，入口 [backend/entrypoint.sh](../../backend/entrypoint.sh)（创建数据目录后启动 uvicorn :8080）。

### 3.2 Docker Compose 启动

```bash
docker-compose up -d
docker-compose logs -f
docker-compose down
```

[docker-compose.yml](../../docker-compose.yml) 单服务，端口 `8080:8080`，数据卷挂载到宿主机：

| 容器路径 | 宿主机路径 | 内容 |
| --- | --- | --- |
| /app/backend/data | ./test_case_generator/data | SQLite + ChromaDB |
| /app/backend/uploads | ./test_case_generator/uploads | 上传文档 |
| /app/backend/outputs | ./test_case_generator/outputs | MD/Excel 结果 |
| /app/backend/logs | ./test_case_generator/logs | 日志 |
| /models/huggingface (ro) | `${LOCAL_EMBEDDING_HOST_PATH:-./models/huggingface}` | 本地 Embedding 模型 cache（只读） |

Docker 环境下 Vue 构建产物由 FastAPI 托管，统一访问 http://localhost:8080（SPA 路由 `/tasks`、`/templates`、`/llm`、`/knowledge` 支持直接访问与刷新，由 `SPAStaticFiles` 回退 `index.html` 实现）。

## 4. 配置说明

### 4.1 基础环境变量（backend/.env 或部署环境）

```dotenv
DEBUG=false
HOST=0.0.0.0
PORT=8080
JWT_SECRET=your-secret-key-change-in-production   # 生产必须修改
MAX_FILE_SIZE=52428800                            # 单文件上限 50MB
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin                              # 生产必须修改
```

完整样例见 [backend/.env.example](../../backend/.env.example)；所有字段定义见 [core/config.py Settings](../../backend/app/core/config.py#L13-L59)。

### 4.2 路径类配置

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite+aiosqlite:///{backend}/data/flow_test.db` | SQLite 连接串 |
| `UPLOAD_DIR` | `{backend}/uploads/` | 主需求与知识库文档上传目录 |
| `OUTPUT_DIR` | `{backend}/outputs/` | 解析文档 / 完整报告 / 总结 / Excel 输出目录 |
| `CHROMA_DIR` | `{backend}/data/chroma/` | ChromaDB 向量数据目录 |

### 4.3 本地 Embedding（知识库）

默认支持本地 `BAAI/bge-small-zh-v1.5`，无需 API Key，但**模型文件需自行准备，系统不会自动下载**：

```dotenv
LOCAL_EMBEDDING_ENABLED=true
LOCAL_EMBEDDING_MODEL_PATH=/absolute/path/to/bge-small-zh-v1.5/snapshots/<revision>
LOCAL_EMBEDDING_DEVICE=cpu
LOCAL_EMBEDDING_BATCH_SIZE=32
LOCAL_EMBEDDING_LOCAL_FILES_ONLY=true
```

模型路径不存在或文件不完整时，知识库会明确报错。Docker 部署需将 HuggingFace cache 根目录只读挂载进容器，并把 `LOCAL_EMBEDDING_CONTAINER_MODEL_PATH` 指向容器内 snapshot 路径（compose 中对应 `LOCAL_EMBEDDING_MODEL_PATH`）。

### 4.4 LangSmith Tracing

默认关闭。开启需同时提供 API Key（否则仅 warning 不生效）：

```dotenv
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-key
LANGSMITH_PROJECT=test-case-generator
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_WORKSPACE_ID=            # 可选
LANGSMITH_HIDE_INPUTS=true         # 默认隐藏需求与生成内容
LANGSMITH_HIDE_OUTPUTS=true
```

配置经 [configure_langsmith_tracing()](../../backend/app/core/config.py#L66-L89) 在应用启动时映射为 LangChain 环境变量。

## 5. 初始登录与使用流程

默认管理员：`admin / admin`（由 `ADMIN_USERNAME` / `ADMIN_PASSWORD` 控制；JWT 有效期默认 24h，`JWT_EXPIRE_HOURS`）。

1. 登录系统。
2. 「模型配置」保存厂商 API Key，测试连接 / 维护模型列表。
3. 可选：「模板管理」创建输出字段模板。
4. 可选：「知识库」创建项目（选 Embedding provider + 模型）并上传业务文档，等待处理完成（processing → ready）。
5. 「任务列表」→ 新建任务：上传主需求文档，选择模型、模板与关联知识库项目。
6. 任务若进入「待澄清」，在澄清对话框提交补充说明（或忽略继续 / 停止生成）。
7. 完成后查看覆盖总结、下载 Excel。

> 单个任务只上传一份主需求文档；多份资料请通过知识库项目上传并在创建任务时关联。

## 6. 运行注意事项

- **单进程假设**：澄清恢复、进度查询、任务停止依赖 `task.py` 中的内存字典与 `InMemorySaver`，请勿以多 worker 方式启动 uvicorn，后端重启会使 CLARIFYING 任务无法恢复。
- **无数据库迁移**：模型变更需删除 `backend/data/flow_test.db` 重建（`init_db()` 会自动建表并插入系统默认模板）。
- **密钥安全**：`JWT_SECRET`、`ADMIN_PASSWORD`、各厂商 API Key 均不应提交仓库；`.env` 已被 gitignore。

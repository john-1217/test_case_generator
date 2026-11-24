# Code Wiki — Test Case Generator

基于 **FastAPI + LangGraph + Vue 3** 的智能测试用例生成平台。用户上传需求文档（PDF/DOC/DOCX/TXT/MD），选择已配置的大语言模型，系统通过 LangGraph 四阶段工作流生成结构化测试用例、覆盖总结，并导出 Excel；同时支持自定义输出模板、知识库 RAG、人机澄清和历史任务管理。

## 文档导航

| 文档 | 内容 |
| --- | --- |
| [01-architecture.md](./01-architecture.md) | 项目整体架构、技术栈、核心数据流（任务工作流 / RAG 检索 / 澄清循环） |
| [02-backend.md](./02-backend.md) | 后端模块职责、API 端点清单、数据模型与枚举状态 |
| [03-frontend.md](./03-frontend.md) | 前端结构：路由、状态管理、API 封装、视图与组件 |
| [04-key-code.md](./04-key-code.md) | 关键类与函数详细说明（工作流、解析器、知识库、结果提取等） |
| [05-dependencies.md](./05-dependencies.md) | 依赖关系：内外部依赖清单、模块依赖图、Provider 支持矩阵 |
| [06-running.md](./06-running.md) | 运行方式：本地开发、Docker 部署、环境变量、登录与配置 |

## 仓库布局

```text
.
├── backend/                  # FastAPI 后端（uv 管理）
│   ├── app/
│   │   ├── main.py           # 应用入口（lifespan 初始化 DB、挂载路由/静态文件）
│   │   ├── api/              # 路由层：auth / task / template / llm_config / knowledge
│   │   ├── core/             # 配置、数据库、安全（JWT/bcrypt）
│   │   ├── models/           # SQLAlchemy ORM 模型
│   │   ├── schemas/          # Pydantic 请求/响应 schema
│   │   └── services/         # 业务服务：工作流、文档解析、知识库、结果提取等
│   ├── config/prompts/       # LangGraph 各阶段 Prompt（role.md + phase1~4）
│   └── tests/                # pytest 测试
├── frontend/                 # Vue 3 + Vite + TypeScript SPA（生产前端）
│   └── src/
│       ├── views/            # 页面：任务 / 模板 / 模型配置 / 知识库 / 登录
│       ├── components/       # 业务组件（task / knowledge / template / ui / layout）
│       ├── stores/           # Pinia 状态（auth / task）
│       ├── services/         # Axios API 封装与类型定义
│       ├── composables/      # 组合式函数（任务轮询）
│       └── router/           # 路由与守卫
├── assets/                   # README 截图
├── Dockerfile                # 多阶段构建（前端构建 + Python 环境 + 静态合并）
├── docker-compose.yml        # 单服务部署，数据卷持久化
└── sample_prd_*.md           # 示例需求文档
```

> 注：仓库中若存在 `frontend-react/` 目录，是保留的 React 旧版实现，仅供回退对照，不参与 Docker 镜像构建。

## 快速开始（速览）

```bash
# 后端（Python 3.11+，uv）
cd backend && uv sync && cp .env.example .env
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# 前端（Node 20+）
cd frontend && npm install && npm run dev   # http://localhost:5174，/api 代理到 8080
```

默认管理员账号 `admin / admin`（可用 `ADMIN_USERNAME` / `ADMIN_PASSWORD` 环境变量覆盖）。详见 [06-running.md](./06-running.md)。

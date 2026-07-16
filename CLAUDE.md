# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Full app / Docker

```bash
# Start the published image used by docker-compose.yml
docker-compose up -d

docker-compose logs -f
docker-compose down

# Build the local multi-stage image from Dockerfile
docker build -t flow-test-engine .
```

Docker serves the combined app on `http://localhost:8080`; API docs are at `http://localhost:8080/docs` and health check at `/health`.

### Backend

```bash
cd backend
uv sync
cp .env.example .env
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

```bash
# Run the backend test suite (pytest is in the dev dependency group)
cd backend && uv run pytest

# Run one backend test
cd backend && uv run pytest path/to/test_file.py::test_name
```

No project test files are currently checked in, so the suite command exits with pytest's “no tests collected” status until tests are added. There is no backend lint/format command configured in `pyproject.toml`; add one before documenting or relying on it.

### React frontend

```bash
cd frontend
npm install
npm run dev       # Vite dev server on localhost:5173, proxies /api to localhost:8080
npm run build     # TypeScript build + Vite production build
npm run lint
npm run preview
```

There is no frontend test script configured in `frontend/package.json`.

### Vue frontend

```bash
cd frontend-vue
npm install
npm run dev       # Vite dev server on localhost:5174, proxies /api to localhost:8080
npm run build     # vue-tsc + Vite production build
npm run preview
```

There is no Vue frontend test script configured in `frontend-vue/package.json`.

## High-level architecture

This is a FastAPI + LangGraph application for generating test cases from requirement documents. The backend owns authentication, document parsing, LLM/provider configuration, task execution, RAG knowledge-base storage, and Excel/Markdown outputs. There are two frontend apps: the original Vite React SPA in `frontend/` and an incremental Vite Vue SPA in `frontend-vue/`; both call the backend under `/api/v1`.

### Backend runtime and routing

- `backend/app/main.py` creates the FastAPI app, initializes the database in the lifespan hook, registers `app.api.router`, exposes `/health`, and mounts `/app/static` when the Docker image includes frontend build output.
- `backend/app/api/__init__.py` mounts all API routes under `/api/v1`:
  - `auth.py`: env-configured admin login only; no registration flow in current code.
  - `task.py`: upload files, create/resume/stop/delete tasks, list tasks, download Excel, read summaries.
  - `template.py`: test-case output template CRUD.
  - `llm_config.py`: provider API key/base URL/model configuration and connection/model-list checks.
  - `knowledge.py`: knowledge-base project CRUD, document ingestion, and vector search.
- `backend/app/core/database.py` uses async SQLAlchemy with SQLite by default and calls `Base.metadata.create_all()` on startup; there is no migration framework.
- `backend/app/core/config.py` reads `.env` via Pydantic settings. Important path settings are `DATABASE_URL`, `UPLOAD_DIR`, `OUTPUT_DIR`, and `CHROMA_DIR`.

### Task generation workflow

The main task flow is in `backend/app/api/task.py` and `backend/app/services/case_generator.py`:

1. `/upload` saves a PDF/DOC/DOCX/TXT/MD file under `UPLOAD_DIR`.
2. `/task/create` validates the selected LLM provider config, optionally builds a template-specific Phase 3 prompt, creates a `Task` row, then starts `_run_workflow` as a FastAPI background task.
3. `_run_workflow` parses the document with `DocumentParser`, saves `<task_id>_parsed_document.md`, optionally retrieves RAG context from a knowledge-base project, then runs `CaseGeneratorWorkflow`.
4. `CaseGeneratorWorkflow` is a LangGraph state graph with four prompt phases loaded from `backend/config/prompts/`: `phase1_analysis`, optional `human_clarification`, `phase2_strategy`, `phase3_generate`, and `phase4_summary`.
5. If Phase 1 requires clarification, the task enters `CLARIFYING`; `/task/{id}/clarify` resumes the in-memory graph from the saved `thread_id`.
6. Finished results go through `ResultExtractor`, which saves full Markdown, a summary Markdown file, and an Excel file extracted from the final Markdown table.

Task progress, cancellation markers, and suspended workflow instances are held in module-level in-memory dictionaries in `task.py`. Clarification resume and current-step progress therefore depend on the same backend process still being alive.

### Documents, outputs, and persistence

- `DocumentParser` uses PyMuPDF for PDFs, `python-docx` for DOC/DOCX, and direct text reads for TXT/MD. PDF parsing extracts embedded text, valid tables, and non-tiny images; it does not perform OCR.
- Default local state lives under `backend/data/`, `backend/uploads/`, and `backend/outputs/`. Docker Compose instead mounts `./flow_test_engine/data`, `./flow_test_engine/uploads`, `./flow_test_engine/outputs`, and logs into the container.
- Generated outputs in `OUTPUT_DIR` include parsed document Markdown, full workflow Markdown, summary Markdown, and `.xlsx` files.

### LLM provider and embedding configuration

- Provider defaults and ordering are in `backend/app/models/llm_config.py` for `openai`, `gemini`, `anthropic`, `deepseek`, `kimi`, and `openrouter`.
- `create_llm()` in `case_generator.py` uses OpenAI-compatible `ChatOpenAI` for OpenAI/DeepSeek/Kimi and has provider-specific branches for Gemini and Anthropic. The optional packages for those branches are not listed in `backend/pyproject.toml`; Gemini falls back to OpenAI-compatible mode, while Anthropic raises an import error if `langchain-anthropic` is unavailable.
- Knowledge-base embeddings are created in `backend/app/services/embedding_service.py`. Only OpenAI, Gemini, and OpenRouter are marked as embedding-supported.

### Knowledge-base / RAG flow

- `knowledge.py` manages projects and document ingestion. Uploaded knowledge documents are parsed in a background task and stored in ChromaDB.
- `KnowledgeBaseService` uses a persistent Chroma client at `CHROMA_DIR`, table-aware Markdown chunking, and collections named `project_<id>`.
- During task generation with `project_id`, `_retrieve_rag_context()` first asks a lightweight LLM to extract up to 10 module/topic queries from the requirement document, searches Chroma per topic, deduplicates chunks by content hash, and injects the assembled context before the source document in Phase 1.

### Frontend structure

- `frontend/src/App.tsx` holds the original React app's top-level auth state, active tab state, task pagination, task polling every 5 seconds, and modal wiring.
- `frontend/src/services/api.ts` is the React app's central Axios API layer. It uses `baseURL: '/api/v1'`, attaches the JWT token from `localStorage`, and redirects to `/` on 401.
- `frontend-vue/` is an incremental Vue 3 + Vite + TypeScript replacement. The task-generation home page and LLM configuration page have been reimplemented; verify the remaining management pages before treating the Vue migration as complete.
- `frontend-vue/src/services/api.ts` mirrors the backend contract, including the model-configuration APIs and `llmConfigService.getModelGroups()` for task creation.
- Vite dev mode proxies `/api` to `http://localhost:8080` in both frontends. The Dockerfile currently builds the React frontend only; update it before expecting Vue output in the container image.

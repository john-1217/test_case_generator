# 04 — 关键类与函数说明

按重要性列出后端核心代码。行号基于当前仓库版本。

## 1. CaseGeneratorWorkflow — [services/case_generator.py](../../backend/app/services/case_generator.py)

LangGraph 四阶段用例生成工作流的核心类。

### 模块级函数

| 函数 | 行号 | 签名 / 说明 |
| --- | --- | --- |
| `load_phase_prompt(phase)` | L23 | 拼接 `config/prompts/role.md` + `{phase}.md` 作为 System Prompt；文件缺失抛 `FileNotFoundError` |
| `load_legacy_prompt()` | L44 | 兼容旧版单文件 `config/prompt.md` |
| `create_llm(provider, api_key, base_url, model)` | L51 | LLM 工厂：openai/deepseek/kimi → `ChatOpenAI`（OpenAI 兼容，base_url 自动补 `/v1`）；gemini → `ChatGoogleGenerativeAI`（缺包时回退 OpenAI 兼容 `/v1beta/openai`）；anthropic → `ChatAnthropic`（缺包抛 ImportError）；其余默认 OpenAI 兼容 |

### WorkflowState（TypedDict，L104）

LangGraph 图状态：`messages`（add_messages 归约）、`document_content`、`images`（`[{caption, base64}]`）、`tables`、`system_prompt`（模板覆盖 Phase3）、`current_step`、`has_clarification`、`clarification_questions`、`report_markdown`、`is_stopped`、`rag_context`、以及各阶段产物 `analysis_result` / `strategy_result` / `cases_markdown` / `summary_result`。

### 类方法

| 方法 | 行号 | 说明 |
| --- | --- | --- |
| `__init__` | L127 | 保存 provider/model/task_id/开关；`create_llm` 建 LLM；`on_step` 进度回调；`InMemorySaver` checkpointer；`_build_graph()` 编译图 |
| `_build_graph()` | L153 | 节点：`phase1_analysis` / `human_clarification` / `phase2_strategy` / `phase3_generate` / `phase4_summary`；边：START→phase1；phase1 条件路由（clarify/continue/end）；clarification 条件路由（continue/re_analyze/end）；phase2→phase3→phase4→END |
| `get_trace_config(thread_id, operation)` | L193 | 生成 LangGraph config：`configurable.thread_id`、run_name、tags、metadata（不含需求内容） |
| `_build_document_content(state)` (static) | L217 | 组装多模态 HumanMessage 内容：RAG 上下文（置于最前）+ 文档 markdown + 表格 + Base64 图片（`image_url`） |
| `_phase1_analysis(state)` | L262 | 文档结构识别 + 需求分析 + 模块对称性检查；检测标记「无法继续生成测试用例，存在以下问题需要澄清」→ `has_clarification`，并截取澄清问题文本 |
| `_phase2_strategy(state)` | L308 | 输入 Phase1 结论 + 原始文档，输出测试策略/闭环验证/自检 |
| `_phase3_generate(state)` | L345 | 有自定义模板时用 `role.md + system_prompt` 替换默认 prompt；输入 Phase1+Phase2+原文档(+RAG)，输出用例 Markdown 表格 |
| `_phase4_summary(state)` | L402 | 输入前三阶段产物，输出覆盖度总结；同时拼接四段为 `report_markdown` |
| `_human_clarification(state)` (static) | L454 | LangGraph `interrupt()` 挂起等待用户输入；「停止生成」→ `is_stopped`；「忽略待澄清内容，继续生成」→ 清除标记；否则将澄清内容追加进 `analysis_result` 供后续阶段使用 |
| `_route_after_phase1(state)` (static) | L489 | `is_stopped`→end；`has_clarification`→clarify；否则 continue |
| `_route_after_clarification(state)` (static) | L498 | `is_stopped`→end；否则 continue |
| `start(parsed_doc, template_prompt, rag_context, thread_id)` | L506 | 初始化状态并 `graph.invoke`；返回 `(thread_id, result)`；thread_id 缺省时生成 UUID |
| `resume(thread_id, clarification_input)` | L547 | `Command(resume=...)` 从 interrupt 点恢复执行 |
| `get_state(thread_id)` | L553 | 读取图当前状态（调试用） |

## 2. 任务编排 — [api/task.py](../../backend/app/api/task.py)

### 模块级内存状态（L33-L37）

`_workflows`（thread_id → workflow 实例）、`_task_progress`（task_id → step）、`_cancelled_tasks`（取消集合）。`TaskCancelledException`（L40）用于中断工作流。

### 端点处理函数

| 函数 | 行号 | 说明 |
| --- | --- | --- |
| `upload_file(file)` | L45 | 校验扩展名与大小，UUID 重命名落盘 `UPLOAD_DIR` |
| `create_task(data, background_tasks, db)` | L69 | 查 `ProviderConfig`（未配置返回 400）；有 template_id 时调 `_build_prompt_with_template`；创建 Task（RUNNING）；`background_tasks.add_task(_run_workflow, ...)` |
| `stop_task(task_id)` | L284 | CLARIFYING → 直接 FAILED；RUNNING → 加入 `_cancelled_tasks`，等待 on_step 检查点抛异常 |
| `clarify_task(task_id, data)` | L315 | 输入「停止生成」→ FAILED；否则状态回 RUNNING，投递 `_resume_workflow` |
| `get_tasks(page, page_size)` | L408 | 按 created_at 倒序分页 |
| `delete_task(task_id)` | L428 | RUNNING/CLARIFYING 拒绝删除；清理输出文件与工作流实例 |
| `download_file(task_id)` | L465 | 校验 FINISHED 与文件存在，`FileResponse` 返回 xlsx |
| `get_summary(task_id)` | L490 | `ResultExtractor.read_summary` 读取总结文本 |

### 后台任务与辅助函数

| 函数 | 行号 | 说明 |
| --- | --- | --- |
| `_run_workflow(task_id, file_path, template_prompt, provider, base_url, api_key, model, project_id)` | L155 | 主流程：分配 thread_id → `asyncio.to_thread` 解析文档（doc_parsing）→ `_save_parsed_document` → 构造 workflow（on_step 回调检查取消并记录进度）→（可选）`_retrieve_rag_context`（rag_retrieval）→ `workflow.start`（线程池）→ 按 `has_clarification` / `report_markdown` / 空结果 分支更新任务状态；异常统一置 FAILED |
| `_finalize_task(task, result, db)` | L265 | 调 `ResultExtractor.extract_and_save`，写回 `output_excel` / `output_summary`，置 FINISHED；提取失败置 FAILED |
| `_resume_workflow(task_id, clarification_input)` | L346 | 从 `_workflows` 取实例（丢失则 FAILED）→ `workflow.resume`（线程池，progress=phase2_strategy）→ 同 _run_workflow 的分支处理 |
| `_task_to_response(task)` | L510 | 组装 TaskResponse；RUNNING 时从 `_task_progress` 读 current_step；有总结时读取内容 |
| `_build_prompt_with_template(fields)` | L534 | 读取 `phase3_generate.md`，正则替换「### 3.3 测试用例输出格式」节为模板字段列表 |
| `_retrieve_rag_context(project_id, document_content, db, provider, ..., trace_config)` | L565 | 三步 RAG：① 建 Embeddings（本地模型先 `local_embedding_status()` 检查；远程则查 `ProviderConfig`）；② 用每厂商轻量模型（`_LITE_MODELS`，L617）提取 ≤10 个模块主题；③ 每主题 `_kb_service.search(top_k=3)`，按内容 hash 去重，拼成「### 参考片段 i（来源：xxx）」上下文；任何异常返回空串不阻断任务 |

## 3. DocumentParser — [services/document_parser.py](../../backend/app/services/document_parser.py)

| 符号 | 行号 | 说明 |
| --- | --- | --- |
| `ParsedDocument`（dataclass） | L17 | 解析产物：`markdown`（正文）、`tables`（`[{caption, markdown}]`）、`images`（`[{caption, base64}]`） |
| `DocumentParser.parse(file_path, extract_images=True)` | L27 | 按扩展名分发：.pdf → PyMuPDF；.docx/.doc → python-docx（.doc 兼容尝试）；.txt/.md → 直接读取 |
| `_parse_pdf_with_pymupdf` | L47 | 逐页提取：文本（排除表格区域）、有效表格、非极小图片；无 OCR |
| `_extract_page_images` | L108 | 提取页面图片并转 base64，过滤尺寸过小的装饰图 |
| `_extract_page_tables` | L146 | `page.find_tables()` 提取表格并转 Markdown |
| `_extract_text_excluding_rects` | L202 | 提取文本时剔除表格矩形区域，避免重复 |
| `_parse_docx(file_path)` (static) | L238 | python-docx 提取段落与表格 |
| `_parse_plaintext(file_path)` (static) | L262 | TXT/MD 直读 |

## 4. KnowledgeBaseService — [services/knowledge_service.py](../../backend/app/services/knowledge_service.py)

| 方法 | 行号 | 说明 |
| --- | --- | --- |
| `__init__` | L29 | 创建 ChromaDB 持久化客户端（`CHROMA_DIR`）与 DocumentParser 实例 |
| `_collection_name(project_id)` (static) | L39 | `project_<id>` |
| `_get_or_create_collection(project_id)` | L43 | 获取/创建项目 collection |
| `_split_with_table_awareness(markdown_content)` | L50 | 表格感知分块：普通文本按 `RecursiveCharacterTextSplitter` 切分；Markdown 表格整体保留，超大表格走 `_split_large_table` 按行切块 |
| `_split_large_table(table_text)` (static) | L128 | 大表按行分块，保留表头 |
| `add_document(project_id, doc_id, file_path, filename, embeddings)` | L165 | 入库：解析 → 分块 → embedding → `collection.add`（metadata 含 filename/doc_id/chunk_index）→ 返回 chunk 数 |
| `remove_document(project_id, doc_id)` | L215 | 按 metadata.doc_id 删除向量 |
| `delete_collection(project_id)` | L228 | 删除整个项目 collection |
| `search(project_id, query, embeddings, top_k)` | L236 | `embed_query` → `collection.query` → 返回 `[{content, metadata, distance}]` |
| `get_collection_stats(project_id)` | L284 | collection chunk 计数等统计 |

## 5. Embedding 服务 — [services/embedding_service.py](../../backend/app/services/embedding_service.py)

| 符号 | 行号 | 说明 |
| --- | --- | --- |
| `is_local_embedding_provider(provider)` | L69 | 是否 `local_huggingface` |
| `local_embedding_status(settings)` | L74 | 检查本地模型路径配置与文件完整性，返回 `(is_ready, message)`；**从不自动下载模型** |
| `LocalHuggingFaceEmbeddings` | L100 | 实现 LangChain `Embeddings` 接口；`__init__`（L103）用 sentence-transformers 加载本地 BGE snapshot；`embed_documents`（L113）/ `embed_query`（L125）按 batch 编码 |
| `_get_local_embeddings(...)` | L137 | 按设置构造本地实例（懒加载缓存） |
| `create_embeddings(provider, api_key, base_url, model)` | L147 | 工厂：local_huggingface / openai（OpenAIEmbeddings）/ gemini / openrouter（OpenAI 兼容） |
| `is_embedding_supported(provider)` | L200 | provider 是否支持 Embedding |
| `get_default_embedding_model(provider)` | L206 | 各 provider 默认 embedding 模型名 |

## 6. ResultExtractor — [services/result_extractor.py](../../backend/app/services/result_extractor.py)

| 方法 | 行号 | 说明 |
| --- | --- | --- |
| `extract_and_save(report_markdown, task_id, filename, cases_markdown, summary_text)` | L19 | 主入口：保存完整报告 MD → 提取表格存 Excel → 保存总结 MD；返回 `(excel_path, summary_path, full_md_path)` |
| `_save_full_markdown` | L56 | 写 `{sanitized_filename}_{task_id}.md` |
| `_extract_table_to_excel` | L66 | 优先用 `cases_markdown`（Phase3 产物），否则从完整报告找最大 Markdown 表格 → DataFrame → openpyxl 写 xlsx |
| `_clean_cell_content` | L90 | 清理单元格内换行/多余符号 |
| `_parse_markdown_table` | L133 | Markdown 表格文本 → `pd.DataFrame` |
| `_save_summary_directly` | L158 | 直接保存 Phase4 的 `summary_result` |
| `_extract_summary` | L168 | 兼容路径：从完整报告中按「覆盖度总结」等标题截取总结 |
| `_sanitize_filename` | L215 | 文件名安全化 |
| `read_summary(summary_path)` | L224 | 读取总结文件内容（供 API 返回） |

## 7. LLM 连接服务 — [services/llm_service.py](../../backend/app/services/llm_service.py)

不依赖 LangChain 的纯 HTTP 实现，用于「模型配置」页的连接测试与模型列表拉取：

| 函数 | 行号 | 说明 |
| --- | --- | --- |
| `_get_headers(provider, api_key)` | L55 | 按厂商构造鉴权 Header（Gemini 用 `x-goog-api-key`，OpenAI 系用 Bearer） |
| `_get_models_url(provider, base_url)` | L73 | 模型列表 URL |
| `_get_chat_url(provider, base_url, model)` | L79 | chat completions URL（Gemini 为 generateContent 路径） |
| `_build_chat_payload(provider, model)` | L88 | 最小 chat 请求体 |
| `test_connection(provider, base_url, api_key, model)` (async) | L112 | 发送测试请求，返回 `(ok, message)` |
| `fetch_models(provider, base_url, api_key)` (async) | L159 | 拉取并归一化远端模型 ID 列表 |
| `get_chat_url` / `get_chat_headers` | L231/L236 | 对外别名导出 |

## 8. 前端关键代码索引

| 代码 | 位置 | 说明 |
| --- | --- | --- |
| Axios 实例与拦截器 | [api.ts L19-L42](../../frontend/src/services/api.ts#L19-L42) | baseURL、token 注入、401 登出 |
| `taskService.downloadFile` | [api.ts L107-L127](../../frontend/src/services/api.ts#L107-L127) | Blob 下载 + Content-Disposition 文件名解析 |
| 路由守卫 | [router/index.ts L21-L32](../../frontend/src/router/index.ts#L21-L32) | 登录态校验与重定向 |
| `useTaskPolling` | [useTaskPolling.ts](../../frontend/src/composables/useTaskPolling.ts) | 5s 轮询任务列表 |
| `CaseGeneratorWorkflow` 对应前端展示 | [ProgressDialog.vue](../../frontend/src/components/task/ProgressDialog.vue) | current_step → 进度可视化 |
| 知识库处理轮询 | [KnowledgeView.vue L59-L96](../../frontend/src/views/KnowledgeView.vue#L59-L96) | processing 文档轮询刷新 |

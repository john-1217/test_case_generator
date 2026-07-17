export const TaskStatus = {
  RUNNING: 0,
  CLARIFYING: 1,
  FINISHED: 2,
  FAILED: 3,
} as const

export type TaskStatus = (typeof TaskStatus)[keyof typeof TaskStatus]

export interface Task {
  task_id: number
  original_filename: string
  created_at: string
  finished_at?: string | null
  status: TaskStatus
  error_message?: string | null
  clarification_message?: string | null
  summary_content?: string | null
  current_step?: string | null
}

export interface TaskListResponse {
  total: number
  tasks: Task[]
}

export interface TemplateField {
  name: string
  description: string
}

export interface Template {
  id: number
  name: string
  fields: TemplateField[]
  is_default: boolean
  is_system: boolean
  created_at: string
  updated_at: string
}

export interface UploadResponse {
  file_path: string
  original_filename: string
}

export interface Project {
  id: number
  name: string
  description?: string | null
  embedding_provider: string
  embedding_model: string
  doc_count: number
  created_at: string
  updated_at: string
}

export interface ProjectListResponse {
  total: number
  projects: Project[]
}

export interface KnowledgeDocument {
  id: number
  project_id: number
  original_filename: string
  file_size: number
  chunk_count: number
  status: 'processing' | 'ready' | 'failed'
  error_message?: string | null
  created_at: string
}

export interface EmbeddingProviderInfo {
  provider: string
  name: string
  default_model: string
  is_configured: boolean
  is_local: boolean
  availability_message?: string | null
}

export interface KnowledgeSearchResult {
  content: string
  metadata: Record<string, unknown>
  distance: number
}

export interface ModelGroup {
  provider: string
  name: string
  models: string[]
}

export interface ProviderListItem {
  provider: string
  name: string
  is_configured: boolean
  is_available: boolean
  model_count: number
}

export interface ProviderModel {
  id: number
  model_name: string
  is_custom: boolean
}

export interface ProviderConfig {
  id: number
  provider: string
  base_url: string
  is_available: boolean
  models: ProviderModel[]
  created_at?: string
  updated_at?: string
}

export interface TestConnectionResponse {
  success: boolean
  message: string
}

export interface FetchModelsResponse {
  success: boolean
  models: string[]
  message: string | null
}

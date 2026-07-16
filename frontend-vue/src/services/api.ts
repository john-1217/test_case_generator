import axios from 'axios'
import type {
  EmbeddingProviderInfo,
  KnowledgeDocument,
  KnowledgeSearchResult,
  FetchModelsResponse,
  ModelGroup,
  Project,
  ProjectListResponse,
  ProviderConfig,
  ProviderListItem,
  TestConnectionResponse,
  Task,
  TaskListResponse,
  Template,
  UploadResponse,
} from './types'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export * from './types'

export const authService = {
  login: async (data: { username: string; password: string }) => {
    const response = await api.post<{ token: string; username: string }>('/auth/login', data)
    return response.data
  },
}

export const taskService = {
  getTasks: async (page = 1, pageSize = 10): Promise<TaskListResponse> => {
    const response = await api.get<TaskListResponse>('/tasks', {
      params: { page, page_size: pageSize },
    })
    return response.data
  },

  uploadFile: async (file: File): Promise<UploadResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post<UploadResponse>('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  createTask: async (data: {
    file_path: string
    original_filename: string
    download_filename?: string
    template_id?: number | null
    provider: string
    model: string
    project_id?: number | null
  }): Promise<Task> => {
    const response = await api.post<Task>('/task/create', data)
    return response.data
  },

  clarifyTask: async (taskId: number, clarificationInput: string): Promise<Task> => {
    const response = await api.post<Task>(`/task/${taskId}/clarify`, {
      clarification_input: clarificationInput,
    })
    return response.data
  },

  stopTask: async (taskId: number): Promise<Task> => {
    const response = await api.post<Task>(`/task/${taskId}/stop`)
    return response.data
  },

  deleteTask: async (taskId: number) => {
    const response = await api.delete(`/tasks/${taskId}`)
    return response.data
  },

  getSummary: async (taskId: number): Promise<{ summary: string }> => {
    const response = await api.get<{ summary: string }>(`/task/${taskId}/summary`)
    return response.data
  },

  getDownloadUrl: (taskId: number) => `/api/v1/download/${taskId}`,

  downloadFile: async (taskId: number) => {
    const response = await api.get(`/download/${taskId}`, { responseType: 'blob' })
    const contentDisposition = response.headers['content-disposition']
    let filename = 'test_cases.xlsx'
    if (contentDisposition) {
      const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
      if (match?.[1]) filename = decodeURIComponent(match[1].replace(/['"]/g, ''))
    }

    const blob = new Blob([response.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  },
}

export const templateService = {
  getTemplates: async (): Promise<Template[]> => {
    const response = await api.get<Template[]>('/templates')
    return response.data
  },

  createTemplate: async (data: {
    name: string
    fields: { name: string; description: string }[]
    is_default?: boolean
  }): Promise<Template> => {
    const response = await api.post<Template>('/templates', data)
    return response.data
  },

  updateTemplate: async (data: {
    id: number
    name: string
    fields: { name: string; description: string }[]
    is_default?: boolean
  }): Promise<Template> => {
    const response = await api.put<Template>('/templates', data)
    return response.data
  },

  deleteTemplate: async (id: number) => {
    const response = await api.delete(`/templates/${id}`)
    return response.data
  },
}

export const llmConfigService = {
  getModelGroups: async (): Promise<ModelGroup[]> => {
    const response = await api.get<ModelGroup[]>('/llm-configs/model-groups')
    return response.data
  },

  getProviderList: async (): Promise<ProviderListItem[]> => {
    const response = await api.get<ProviderListItem[]>('/llm-configs/provider-list')
    return response.data
  },

  getProviderConfig: async (provider: string): Promise<ProviderConfig | null> => {
    const response = await api.get<ProviderConfig | null>(`/llm-configs/provider-configs/${provider}`)
    return response.data
  },

  saveProviderConfig: async (
    provider: string,
    data: { base_url: string; api_key: string },
  ): Promise<ProviderConfig> => {
    const response = await api.put<ProviderConfig>(`/llm-configs/provider-configs/${provider}`, data)
    return response.data
  },

  fetchModels: async (
    provider: string,
    data: { base_url: string; api_key: string },
  ): Promise<FetchModelsResponse> => {
    const response = await api.post<FetchModelsResponse>(
      `/llm-configs/provider-configs/${provider}/fetch-models`,
      data,
    )
    return response.data
  },

  addModel: async (provider: string, modelName: string) => {
    const response = await api.post(`/llm-configs/provider-configs/${provider}/models`, {
      model_name: modelName,
    })
    return response.data
  },

  deleteModel: async (provider: string, modelName: string) => {
    const response = await api.delete(
      `/llm-configs/provider-configs/${provider}/models/${encodeURIComponent(modelName)}`,
    )
    return response.data
  },

  testModel: async (
    provider: string,
    modelName: string,
    data: { base_url: string; api_key: string },
  ): Promise<TestConnectionResponse> => {
    const response = await api.post<TestConnectionResponse>(
      `/llm-configs/provider-configs/${provider}/models/${encodeURIComponent(modelName)}/test`,
      data,
    )
    return response.data
  },
}

export const knowledgeService = {
  getEmbeddingProviders: async (): Promise<EmbeddingProviderInfo[]> => {
    const response = await api.get<EmbeddingProviderInfo[]>('/knowledge/embedding-providers')
    return response.data
  },

  getProjects: async (): Promise<ProjectListResponse> => {
    const response = await api.get<ProjectListResponse>('/knowledge/projects')
    return response.data
  },

  getProject: async (id: number): Promise<Project> => {
    const response = await api.get<Project>(`/knowledge/projects/${id}`)
    return response.data
  },

  createProject: async (data: {
    name: string
    description?: string
    embedding_provider: string
    embedding_model: string
  }): Promise<Project> => {
    const response = await api.post<Project>('/knowledge/projects', data)
    return response.data
  },

  updateProject: async (
    id: number,
    data: {
      name?: string
      description?: string
      embedding_provider?: string
      embedding_model?: string
    },
  ): Promise<Project> => {
    const response = await api.put<Project>(`/knowledge/projects/${id}`, data)
    return response.data
  },

  deleteProject: async (id: number) => {
    const response = await api.delete(`/knowledge/projects/${id}`)
    return response.data
  },

  getDocuments: async (projectId: number): Promise<KnowledgeDocument[]> => {
    const response = await api.get<KnowledgeDocument[]>(`/knowledge/projects/${projectId}/documents`)
    return response.data
  },

  uploadDocument: async (projectId: number, file: File): Promise<KnowledgeDocument> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post<KnowledgeDocument>(
      `/knowledge/projects/${projectId}/documents`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000,
      },
    )
    return response.data
  },

  deleteDocument: async (docId: number) => {
    const response = await api.delete(`/knowledge/documents/${docId}`)
    return response.data
  },

  search: async (
    projectId: number,
    query: string,
    topK = 5,
  ): Promise<{ results: KnowledgeSearchResult[] }> => {
    const response = await api.post<{ results: KnowledgeSearchResult[] }>(
      `/knowledge/projects/${projectId}/search`,
      { query, top_k: topK },
    )
    return response.data
  },
}

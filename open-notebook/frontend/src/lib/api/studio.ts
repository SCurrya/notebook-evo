// Studio 模块 API 客户端
// 提供模板管理、报告生成、FAQ 生成、时间线生成的接口调用

import apiClient from './client'

// === Studio 类型定义 ===

export interface StudioTemplate {
  id: string
  name: string
  description: string
  prompt: string
  output_format: string
  created_at: string
  updated_at: string
}

export interface CreateStudioTemplateRequest {
  name: string
  description?: string
  prompt: string
  output_format?: string
}

export interface UpdateStudioTemplateRequest {
  name?: string
  description?: string
  prompt?: string
  output_format?: string
}

export type ReportType = 'academic' | 'business' | 'brief'

export interface ReportGenerateRequest {
  notebook_id: string
  report_type: ReportType
}

export interface ReportGenerateResponse {
  report: string
  report_type: string
  notebook_id: string
}

export interface FAQItem {
  question: string
  answer: string
}

export interface FAQGenerateRequest {
  notebook_id: string
  num_questions?: number
}

export interface FAQGenerateResponse {
  faqs: FAQItem[]
  notebook_id: string
}

export interface TimelineEvent {
  date: string
  event: string
}

export interface TimelineGenerateRequest {
  notebook_id: string
}

export interface TimelineGenerateResponse {
  events: TimelineEvent[]
  notebook_id: string
}

// === Studio API 客户端 ===

export const studioApi = {
  // --- 模板管理 ---
  listTemplates: async () => {
    const response = await apiClient.get<StudioTemplate[]>('/v1/studio/templates')
    return response.data
  },

  getTemplate: async (id: string) => {
    const response = await apiClient.get<StudioTemplate>(`/v1/studio/templates/${id}`)
    return response.data
  },

  createTemplate: async (data: CreateStudioTemplateRequest) => {
    const response = await apiClient.post<StudioTemplate>('/v1/studio/templates', data)
    return response.data
  },

  updateTemplate: async (id: string, data: UpdateStudioTemplateRequest) => {
    const response = await apiClient.put<StudioTemplate>(`/v1/studio/templates/${id}`, data)
    return response.data
  },

  deleteTemplate: async (id: string) => {
    await apiClient.delete(`/v1/studio/templates/${id}`)
  },

  // --- 报告生成 ---
  generateReport: async (data: ReportGenerateRequest) => {
    const response = await apiClient.post<ReportGenerateResponse>('/v1/studio/report/generate', data)
    return response.data
  },

  // --- FAQ 生成 ---
  generateFAQ: async (data: FAQGenerateRequest) => {
    const response = await apiClient.post<FAQGenerateResponse>('/v1/studio/faq/generate', data)
    return response.data
  },

  // --- 时间线生成 ---
  generateTimeline: async (data: TimelineGenerateRequest) => {
    const response = await apiClient.post<TimelineGenerateResponse>('/v1/studio/timeline/generate', data)
    return response.data
  },
}

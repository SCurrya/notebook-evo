import apiClient from './client'

export interface AnalyticsSummary {
  counts: {
    notebook: number
    source: number
    note: number
    insight: number
    task: number
    entity: number
    relation: number
  }
  recent_notebooks: Array<{
    id: string
    name: string
    updated?: string
  }>
  generated_at: string
  error?: string
}

export const analyticsApi = {
  summary: async () => {
    const response = await apiClient.get<AnalyticsSummary>('/analytics/summary')
    return response.data
  },
}

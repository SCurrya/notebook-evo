// 系统健康状态 API 客户端
import apiClient from './client'

export interface SystemStatus {
  ok: boolean
  version: string
  uptime_seconds: number
  timestamp: string
  python: string
  platform: string
  db: {
    connected: boolean
    error?: string
  }
  models: {
    count: number
    by_provider: Record<string, number>
    error?: string
  }
  worker: {
    running: boolean
    max_tasks: string | number | null
    error?: string
  }
}

export const systemApi = {
  getStatus: async (): Promise<SystemStatus> => {
    const response = await apiClient.get<SystemStatus>('/system/status')
    return response.data
  },
}

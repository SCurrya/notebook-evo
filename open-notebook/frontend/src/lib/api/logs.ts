/**
 * Log management API client.
 */

import apiClient from './client'
import { getApiUrl } from '@/lib/config'
import type {
  ClearAllLogsResult,
  ClearLogResult,
  LogEntry,
  LogFile,
} from '@/lib/types/logs'

export const logsApi = {
  listFiles: async (): Promise<LogFile[]> => {
    const response = await apiClient.get<LogFile[]>('/logs/files')
    return response.data
  },

  readLog: async (
    filename: string,
    options: {
      maxLines?: number
      level?: string
      search?: string
      reverse?: boolean
    } = {}
  ): Promise<LogEntry[]> => {
    const response = await apiClient.get<LogEntry[]>(`/logs/${encodeURIComponent(filename)}`, {
      params: {
        max_lines: options.maxLines ?? 1000,
        level: options.level,
        search: options.search,
        reverse: options.reverse ?? true,
      },
    })
    return response.data
  },

  downloadLogUrl: async (filename: string): Promise<string> => {
    const base = await getApiUrl()
    return `${base}/api/logs/${encodeURIComponent(filename)}/download`
  },

  clearLog: async (filename: string): Promise<ClearLogResult> => {
    const response = await apiClient.delete<ClearLogResult>(
      `/logs/${encodeURIComponent(filename)}`
    )
    return response.data
  },

  clearAllLogs: async (): Promise<ClearAllLogsResult> => {
    const response = await apiClient.delete<ClearAllLogsResult>('/logs')
    return response.data
  },
}

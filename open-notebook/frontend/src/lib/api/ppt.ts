/**
 * PPT 生成 API 客户端。
 *
 * 通过 open-notebook 后端 /api/ppt 端点生成 .pptx 文件。
 */

import apiClient from './client'
import type {
  PPTGenerationRequest,
  PPTTaskListResponse,
  PPTTaskResponse,
  PPTTaskStatus,
  PPTTemplate,
} from '@/lib/types/ppt'

export const pptApi = {
  /**
   * 列出所有可用的 PPT 模板。
   */
  listTemplates: async (): Promise<PPTTemplate[]> => {
    const response = await apiClient.get<PPTTemplate[]>('/ppt/templates')
    return response.data
  },

  /**
   * 提交 PPT 生成任务。
   * 立即返回 task ID；生成在后台异步执行。
   */
  generate: async (
    request: PPTGenerationRequest
  ): Promise<PPTTaskResponse> => {
    const response = await apiClient.post<PPTTaskResponse>(
      '/ppt/generate',
      request
    )
    return response.data
  },

  /**
   * 获取 PPT 生成任务状态。
   */
  getTask: async (taskId: string): Promise<PPTTaskStatus> => {
    const response = await apiClient.get<PPTTaskStatus>(
      `/ppt/tasks/${taskId}`
    )
    return response.data
  },

  /**
   * 分页列出 PPT 生成任务。
   */
  listTasks: async (
    page: number = 1,
    pageSize: number = 20
  ): Promise<PPTTaskListResponse> => {
    const response = await apiClient.get<PPTTaskListResponse>('/ppt/tasks', {
      params: { page, page_size: pageSize },
    })
    return response.data
  },

  /**
   * 获取生成文件的下载 URL（相对路径，需拼接 API base URL）。
   */
  getDownloadUrl: (taskId: string): string => {
    return `/ppt/tasks/${taskId}/download`
  },

  /**
   * 删除 PPT 生成任务及其文件。
   */
  deleteTask: async (taskId: string): Promise<void> => {
    await apiClient.delete(`/ppt/tasks/${taskId}`)
  },
}

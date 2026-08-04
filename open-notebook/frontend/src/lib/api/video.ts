/**
 * Video generation API client.
 *
 * Proxies requests to the MoneyPrinterTurbo microservice through the
 * open-notebook backend at /api/videos.
 */

import apiClient from './client'
import type {
  TemplateCreateRequest,
  VideoGenerationRequest,
  VideoServiceHealth,
  VideoTaskListResponse,
  VideoTaskResponse,
  VideoTaskStatus,
  VideoTemplateListResponse,
} from '@/lib/types/video'

export const videoApi = {
  /**
   * Check if the MoneyPrinterTurbo video service is available.
   */
  checkHealth: async (): Promise<VideoServiceHealth> => {
    const response = await apiClient.get<VideoServiceHealth>('/videos/health')
    return response.data
  },

  /**
   * 列出所有可用的视频模板。
   *
   * 返回营销、教程、故事、新闻、短视频等预设模板，
   * 每个模板包含节奏、配音、BGM、字幕等预设参数。
   */
  listTemplates: async (): Promise<VideoTemplateListResponse> => {
    const response = await apiClient.get<VideoTemplateListResponse>(
      '/videos/templates'
    )
    return response.data
  },

  /**
   * Submit a new video generation task.
   * Returns immediately with a task ID; generation runs asynchronously.
   */
  createTask: async (
    request: VideoGenerationRequest
  ): Promise<VideoTaskResponse> => {
    const response = await apiClient.post<VideoTaskResponse>('/videos', request)
    return response.data
  },

  /**
   * 基于预设模板创建视频生成任务。
   *
   * 根据模板名称加载预设参数，结合主题与可选覆盖项构建请求，
   * 然后提交到 MoneyPrinterTurbo 服务。
   *
   * @param templateName 模板标识: marketing/tutorial/story/news/short
   * @param subject 视频主题/标题
   * @param overrides 覆盖模板预设参数的可选字典
   */
  createFromTemplate: async (
    templateName: string,
    subject: string,
    overrides?: Partial<VideoGenerationRequest>
  ): Promise<VideoTaskResponse> => {
    const payload: TemplateCreateRequest = {
      template_name: templateName,
      subject,
      custom_overrides: overrides,
    }
    const response = await apiClient.post<VideoTaskResponse>(
      '/videos/from-template',
      payload
    )
    return response.data
  },

  /**
   * Get the status of a video generation task.
   */
  getTask: async (taskId: string): Promise<VideoTaskStatus> => {
    const response = await apiClient.get<VideoTaskStatus>(
      `/videos/${taskId}`
    )
    return response.data
  },

  /**
   * List video generation tasks (paginated).
   */
  listTasks: async (
    page: number = 1,
    pageSize: number = 20
  ): Promise<VideoTaskListResponse> => {
    const response = await apiClient.get<VideoTaskListResponse>('/videos', {
      params: { page, page_size: pageSize },
    })
    return response.data
  },

  /**
   * Delete a video task and its artifacts.
   */
  deleteTask: async (taskId: string): Promise<void> => {
    await apiClient.delete(`/videos/${taskId}`)
  },

  /**
   * 触发后端一键启动 MoneyPrinterTurbo 服务。
   *
   * 后端会尝试在 MPT_PROJECT_DIR 目录下用 python main.py 启动服务，
   * 返回的是同步结果（启动是否成功），并不代表服务已就绪。
   * 客户端需要继续轮询 checkHealth 验证服务可用性。
   */
  launchMpt: async (): Promise<{
    success: boolean
    message: string
    pid?: number
    log_path?: string
    url?: string
  }> => {
    const response = await apiClient.post<{
      success: boolean
      message: string
      pid?: number
      log_path?: string
      url?: string
    }>('/videos/launch-mpt')
    return response.data
  },
}

/**
 * Image generation API client.
 *
 * Proxies requests to the open-notebook backend at /api/images, which
 * supports OpenAI DALL-E, Stability AI, and an offline placeholder
 * provider.
 */

import apiClient from './client'
import type {
  ImageGenerationRequest,
  ImageGenerationResponse,
  ImageProviderInfo,
  ImageTaskListResponse,
  ImageTaskStatus,
} from '@/lib/types/image'

export const imageApi = {
  /**
   * List available image providers and their configuration status.
   */
  listProviders: async (): Promise<ImageProviderInfo[]> => {
    const response = await apiClient.get<ImageProviderInfo[]>(
      '/images/providers'
    )
    return response.data
  },

  /**
   * Submit a new image generation task.
   * Returns immediately with a task ID; generation runs asynchronously.
   */
  generate: async (
    request: ImageGenerationRequest
  ): Promise<ImageGenerationResponse> => {
    const response = await apiClient.post<ImageGenerationResponse>(
      '/images/generate',
      request
    )
    return response.data
  },

  /**
   * Get the status of a single image generation task.
   */
  getTask: async (taskId: string): Promise<ImageTaskStatus> => {
    const response = await apiClient.get<ImageTaskStatus>(
      `/images/tasks/${taskId}`
    )
    return response.data
  },

  /**
   * List image generation tasks (paginated, newest-first).
   */
  listTasks: async (
    page: number = 1,
    pageSize: number = 20
  ): Promise<ImageTaskListResponse> => {
    const response = await apiClient.get<ImageTaskListResponse>(
      '/images/tasks',
      { params: { page, page_size: pageSize } }
    )
    return response.data
  },

  /**
   * Build the relative download URL for a generated image.
   *
   * The returned path is served by the backend at
   * /api/images/tasks/{taskId}/download?index={index} and proxied
   * through the Next.js rewrites, so it can be used directly in
   * <img src> or <a href>.
   */
  getDownloadUrl: (taskId: string, index: number = 0): string => {
    return `/api/images/tasks/${taskId}/download?index=${index}`
  },

  /**
   * Delete an image task and its generated files.
   */
  deleteTask: async (taskId: string): Promise<void> => {
    await apiClient.delete(`/images/tasks/${taskId}`)
  },
}

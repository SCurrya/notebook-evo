/**
 * PDF generation API client.
 *
 * Communicates with the open-notebook backend at /api/pdf/* which
 * generates PDFs server-side using reportlab (no browser printing).
 */

import apiClient from './client'
import type {
  PDFGenerationRequest,
  PDFTaskListResponse,
  PDFTaskResponse,
  PDFTaskStatus,
  PDFTemplate,
} from '@/lib/types/pdf'

export const pdfApi = {
  /**
   * List all available PDF templates.
   */
  listTemplates: async (): Promise<PDFTemplate[]> => {
    const response = await apiClient.get<PDFTemplate[]>('/pdf/templates')
    return response.data
  },

  /**
   * Submit a new PDF generation task.
   * Returns immediately with a task ID; generation runs asynchronously.
   */
  generate: async (
    request: PDFGenerationRequest
  ): Promise<PDFTaskResponse> => {
    const response = await apiClient.post<PDFTaskResponse>(
      '/pdf/generate',
      request
    )
    return response.data
  },

  /**
   * Get the status of a single PDF generation task.
   */
  getTask: async (taskId: string): Promise<PDFTaskStatus> => {
    const response = await apiClient.get<PDFTaskStatus>(
      `/pdf/tasks/${taskId}`
    )
    return response.data
  },

  /**
   * List PDF generation tasks (paginated, newest first).
   */
  listTasks: async (
    page: number = 1,
    pageSize: number = 20
  ): Promise<PDFTaskListResponse> => {
    const response = await apiClient.get<PDFTaskListResponse>('/pdf/tasks', {
      params: { page, page_size: pageSize },
    })
    return response.data
  },

  /**
   * Build the download URL for a completed PDF task.
   *
   * Returns a relative URL (resolved against the API base URL by the
   * browser). Use this as an <a href> or window.open target.
   */
  getDownloadUrl: (taskId: string): string => {
    return `/api/pdf/tasks/${taskId}/download`
  },

  /**
   * Delete a PDF task and its generated file.
   */
  deleteTask: async (taskId: string): Promise<void> => {
    await apiClient.delete(`/pdf/tasks/${taskId}`)
  },
}

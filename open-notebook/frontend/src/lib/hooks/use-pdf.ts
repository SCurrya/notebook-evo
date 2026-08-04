/**
 * React Query hooks for PDF generation.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { pdfApi } from '@/lib/api/pdf'
import type { PDFGenerationRequest } from '@/lib/types/pdf'

const QUERY_KEYS = {
  templates: ['pdf', 'templates'] as const,
  tasks: (page: number, pageSize: number) =>
    ['pdf', 'tasks', page, pageSize] as const,
  task: (taskId: string) => ['pdf', 'task', taskId] as const,
}

/**
 * List all available PDF templates.
 */
export function usePdfTemplates() {
  return useQuery({
    queryKey: QUERY_KEYS.templates,
    queryFn: () => pdfApi.listTemplates(),
    staleTime: 5 * 60_000, // 5 minutes - templates rarely change
  })
}

/**
 * List PDF generation tasks (paginated, newest first).
 *
 * Polls every 5 seconds while there are active tasks so the UI
 * reflects progress without manual refresh.
 */
export function usePdfTasks(page: number = 1, pageSize: number = 20) {
  return useQuery({
    queryKey: QUERY_KEYS.tasks(page, pageSize),
    queryFn: () => pdfApi.listTasks(page, pageSize),
    refetchInterval: 5_000, // Poll every 5s for active tasks
  })
}

/**
 * Get a single PDF task status (with polling for active tasks).
 *
 * Polls every 2 seconds while the task is pending or processing,
 * and stops once the task reaches a terminal state (completed/failed).
 */
export function usePdfTask(taskId: string | null) {
  return useQuery({
    queryKey: taskId ? QUERY_KEYS.task(taskId) : ['pdf', 'task', 'none'],
    queryFn: () => pdfApi.getTask(taskId!),
    enabled: !!taskId,
    refetchInterval: (query) => {
      const state = query.state.data?.state
      // Poll every 2s while task is active; stop when completed/failed
      if (state && !['completed', 'failed'].includes(state)) {
        return 2_000
      }
      return false
    },
  })
}

/**
 * Submit a new PDF generation task.
 *
 * Invalidates the task list query on success so the new task
 * appears immediately.
 */
export function useCreatePdfTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (request: PDFGenerationRequest) => pdfApi.generate(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pdf', 'tasks'] })
    },
  })
}

/**
 * Delete a PDF task and its generated file.
 *
 * Invalidates the task list query on success so the removed task
 * disappears immediately.
 */
export function useDeletePdfTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (taskId: string) => pdfApi.deleteTask(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pdf', 'tasks'] })
    },
  })
}

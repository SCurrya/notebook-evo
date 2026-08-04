/**
 * React Query hooks for image generation.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { imageApi } from '@/lib/api/image'
import type { ImageGenerationRequest } from '@/lib/types/image'

const QUERY_KEYS = {
  providers: ['image', 'providers'] as const,
  tasks: (page: number, pageSize: number) =>
    ['image', 'tasks', page, pageSize] as const,
  task: (taskId: string) => ['image', 'task', taskId] as const,
}

/**
 * List available image providers and their configuration status.
 */
export function useImageProviders() {
  return useQuery({
    queryKey: QUERY_KEYS.providers,
    queryFn: () => imageApi.listProviders(),
    staleTime: 60_000, // 1 minute
    retry: 1,
  })
}

/**
 * List image generation tasks (paginated). Polls while any task is active.
 */
export function useImageTasks(page: number = 1, pageSize: number = 20) {
  return useQuery({
    queryKey: QUERY_KEYS.tasks(page, pageSize),
    queryFn: () => imageApi.listTasks(page, pageSize),
    refetchInterval: (query) => {
      // 有进行中的任务时每 3 秒轮询一次
      const items = query.state.data?.items ?? []
      const hasActive = items.some(
        (t) => !['completed', 'failed'].includes(t.state)
      )
      return hasActive ? 3_000 : false
    },
  })
}

/**
 * Get a single image task status (with polling for active tasks).
 */
export function useImageTask(taskId: string | null) {
  return useQuery({
    queryKey: taskId ? QUERY_KEYS.task(taskId) : ['image', 'task', 'none'],
    queryFn: () => imageApi.getTask(taskId!),
    enabled: !!taskId,
    refetchInterval: (query) => {
      const state = query.state.data?.state
      if (state && !['completed', 'failed'].includes(state)) {
        return 2_000
      }
      return false
    },
  })
}

/**
 * Submit a new image generation task.
 */
export function useCreateImageTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (request: ImageGenerationRequest) =>
      imageApi.generate(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image', 'tasks'] })
    },
  })
}

/**
 * Delete an image task and its generated files.
 */
export function useDeleteImageTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (taskId: string) => imageApi.deleteTask(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image', 'tasks'] })
    },
  })
}

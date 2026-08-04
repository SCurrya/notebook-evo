/**
 * React Query hooks for video generation.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { videoApi } from '@/lib/api/video'
import type { VideoGenerationRequest } from '@/lib/types/video'

const QUERY_KEYS = {
  health: ['video', 'health'] as const,
  templates: ['video', 'templates'] as const,
  tasks: (page: number, pageSize: number) =>
    ['video', 'tasks', page, pageSize] as const,
  task: (taskId: string) => ['video', 'task', taskId] as const,
}

/**
 * Check if the MoneyPrinterTurbo video service is available.
 */
export function useVideoServiceHealth() {
  return useQuery({
    queryKey: QUERY_KEYS.health,
    queryFn: () => videoApi.checkHealth(),
    staleTime: 30_000, // 30 seconds
    retry: 1,
  })
}

/**
 * 列出所有可用的视频模板。
 *
 * 模板列表为静态预设，缓存时间较长以减少请求。
 */
export function useVideoTemplates() {
  return useQuery({
    queryKey: QUERY_KEYS.templates,
    queryFn: () => videoApi.listTemplates(),
    staleTime: 5 * 60_000, // 5 minutes
    retry: 1,
  })
}

/**
 * List video generation tasks.
 */
export function useVideoTasks(page: number = 1, pageSize: number = 20) {
  return useQuery({
    queryKey: QUERY_KEYS.tasks(page, pageSize),
    queryFn: () => videoApi.listTasks(page, pageSize),
    refetchInterval: 5_000, // Poll every 5s for active tasks
  })
}

/**
 * Get a single video task status (with polling for active tasks).
 */
export function useVideoTask(taskId: string | null) {
  return useQuery({
    queryKey: taskId ? QUERY_KEYS.task(taskId) : ['video', 'task', 'none'],
    queryFn: () => videoApi.getTask(taskId!),
    enabled: !!taskId,
    refetchInterval: (query) => {
      const state = query.state.data?.state
      // Poll every 2s while task is active; stop when completed/failed
      if (
        state &&
        !['completed', 'failed'].includes(state)
      ) {
        return 2_000
      }
      return false
    },
  })
}

/**
 * Submit a new video generation task.
 */
export function useCreateVideoTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (request: VideoGenerationRequest) =>
      videoApi.createTask(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['video', 'tasks'] })
    },
  })
}

/**
 * 基于预设模板创建视频生成任务。
 *
 * @param templateName 模板标识
 * @param subject 视频主题
 * @param overrides 覆盖模板预设参数的可选字典
 */
export function useCreateVideoFromTemplate() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      templateName,
      subject,
      overrides,
    }: {
      templateName: string
      subject: string
      overrides?: Partial<VideoGenerationRequest>
    }) => videoApi.createFromTemplate(templateName, subject, overrides),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['video', 'tasks'] })
    },
  })
}

/**
 * Delete a video task.
 */
export function useDeleteVideoTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (taskId: string) => videoApi.deleteTask(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['video', 'tasks'] })
    },
  })
}

/**
 * 一键启动 MoneyPrinterTurbo 后端服务（桌面端专用）。
 *
 * 返回后会让 health 查询自动 invalidate，便于 UI 显示最新的服务状态。
 */
export function useLaunchMpt() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => videoApi.launchMpt(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['video', 'health'] })
    },
  })
}

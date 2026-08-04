/**
 * React Query hooks for PPT generation.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { pptApi } from '@/lib/api/ppt'
import type { PPTGenerationRequest } from '@/lib/types/ppt'

const QUERY_KEYS = {
  templates: ['ppt', 'templates'] as const,
  tasks: (page: number, pageSize: number) =>
    ['ppt', 'tasks', page, pageSize] as const,
  task: (taskId: string) => ['ppt', 'task', taskId] as const,
}

/**
 * 列出所有可用的 PPT 模板。
 */
export function usePptTemplates() {
  return useQuery({
    queryKey: QUERY_KEYS.templates,
    queryFn: () => pptApi.listTemplates(),
    staleTime: 5 * 60 * 1000, // 5 分钟内不重新请求
  })
}

/**
 * 分页列出 PPT 生成任务。
 */
export function usePptTasks(page: number = 1, pageSize: number = 20) {
  return useQuery({
    queryKey: QUERY_KEYS.tasks(page, pageSize),
    queryFn: () => pptApi.listTasks(page, pageSize),
    refetchInterval: 5_000, // 每 5s 轮询一次（用于活跃任务）
  })
}

/**
 * 获取单个 PPT 任务状态（活跃任务自动轮询）。
 */
export function usePptTask(taskId: string | null) {
  return useQuery({
    queryKey: taskId ? QUERY_KEYS.task(taskId) : ['ppt', 'task', 'none'],
    queryFn: () => pptApi.getTask(taskId!),
    enabled: !!taskId,
    refetchInterval: (query) => {
      const state = query.state.data?.state
      // 活跃任务每 2s 轮询；完成/失败后停止
      if (state && !['completed', 'failed'].includes(state)) {
        return 2_000
      }
      return false
    },
  })
}

/**
 * 提交新的 PPT 生成任务。
 */
export function useCreatePptTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (request: PPTGenerationRequest) => pptApi.generate(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ppt', 'tasks'] })
    },
  })
}

/**
 * 删除 PPT 任务。
 */
export function useDeletePptTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (taskId: string) => pptApi.deleteTask(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ppt', 'tasks'] })
    },
  })
}

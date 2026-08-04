/**
 * React Query hooks for log management.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { logsApi } from '@/lib/api/logs'

const QUERY_KEYS = {
  files: ['logs', 'files'] as const,
  entries: (filename: string, level?: string, search?: string) =>
    ['logs', 'entries', filename, level ?? 'all', search ?? ''] as const,
}

export function useLogFiles() {
  return useQuery({
    queryKey: QUERY_KEYS.files,
    queryFn: () => logsApi.listFiles(),
    staleTime: 10_000,
  })
}

export function useLogEntries(
  filename: string | null,
  options: {
    level?: string
    search?: string
    maxLines?: number
    autoRefresh?: boolean
  } = {}
) {
  const { level, search, maxLines, autoRefresh } = options
  return useQuery({
    queryKey: filename
      ? QUERY_KEYS.entries(filename, level, search)
      : ['logs', 'entries', 'none'],
    queryFn: () =>
      logsApi.readLog(filename!, {
        maxLines,
        level: level === 'all' ? undefined : level,
        search: search?.trim() || undefined,
        reverse: true,
      }),
    enabled: !!filename,
    refetchInterval: autoRefresh ? 3_000 : false,
  })
}

export function useClearLog() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (filename: string) => logsApi.clearLog(filename),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logs'] })
    },
  })
}

export function useClearAllLogs() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => logsApi.clearAllLogs(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logs'] })
    },
  })
}

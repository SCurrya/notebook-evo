'use client'

// 系统健康状态 hooks
import { useQuery } from '@tanstack/react-query'
import { systemApi } from '@/lib/api/system'

export function useSystemStatus() {
  return useQuery({
    queryKey: ['system-status'],
    queryFn: systemApi.getStatus,
    refetchInterval: 30_000, // 每 30 秒刷新
    retry: 1,
  })
}

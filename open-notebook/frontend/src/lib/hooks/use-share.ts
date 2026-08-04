// 共享 React Query hooks
// 提供共享链接的查询和变更操作

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { shareApi } from '@/lib/api/share'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorMessage } from '@/lib/utils/error-handler'
import type { CreateShareLinkRequest } from '@/lib/api/share'

// 列出笔记本的所有共享链接
export function useShareLinks(notebookId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.shareLinks(notebookId),
    queryFn: () => shareApi.list(notebookId),
    enabled: !!notebookId,
  })
}

// 获取共享笔记本（通过 token）
export function useSharedNotebook(token: string) {
  return useQuery({
    queryKey: QUERY_KEYS.sharedNotebook(token),
    queryFn: () => shareApi.get(token),
    enabled: !!token,
  })
}

// 创建共享链接
export function useCreateShareLink() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: ({
      notebookId,
      data,
    }: {
      notebookId: string
      data: CreateShareLinkRequest
    }) => shareApi.create(notebookId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.shareLinks(variables.notebookId),
      })
      toast({
        title: t('common.success'),
        description: '共享链接已创建',
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t('common.error'),
        description: getApiErrorMessage(error, t, 'apiErrors.genericError'),
        variant: 'destructive',
      })
    },
  })
}

// 撤销共享链接
export function useRevokeShareLink() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (linkId: string) => shareApi.revoke(linkId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['share'] })
      toast({
        title: t('common.success'),
        description: '共享链接已撤销',
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t('common.error'),
        description: getApiErrorMessage(error, t, 'apiErrors.genericError'),
        variant: 'destructive',
      })
    },
  })
}

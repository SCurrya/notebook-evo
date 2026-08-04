// API Key 管理 React Query hooks
// 提供 API Key 的查询和变更操作

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiKeysApi } from '@/lib/api/api-keys'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorMessage } from '@/lib/utils/error-handler'
import type { CreateApiKeyRequest } from '@/lib/api/api-keys'

// 列出所有 API Keys
export function useApiKeys() {
  return useQuery({
    queryKey: QUERY_KEYS.apiKeys,
    queryFn: () => apiKeysApi.list(),
  })
}

// 创建 API Key
export function useCreateApiKey() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: CreateApiKeyRequest) => apiKeysApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.apiKeys })
      toast({
        title: t('common.success'),
        description: 'API Key 创建成功',
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

// 撤销 API Key
export function useRevokeApiKey() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (keyId: string) => apiKeysApi.revoke(keyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.apiKeys })
      toast({
        title: t('common.success'),
        description: 'API Key 已撤销',
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

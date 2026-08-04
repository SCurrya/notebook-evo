// 知识图谱 React Query hooks
// 提供知识图谱数据的查询和变更操作

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { knowledgeGraphApi } from '@/lib/api/knowledge-graph'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorMessage } from '@/lib/utils/error-handler'
import type {
  CreateEntityRequest,
  CreateRelationRequest,
  ExtractGraphRequest,
} from '@/lib/api/knowledge-graph'

// 获取笔记本的知识图谱
export function useKnowledgeGraph(notebookId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.knowledgeGraph(notebookId),
    queryFn: () => knowledgeGraphApi.get(notebookId),
    enabled: !!notebookId,
  })
}

// GraphRAG 问答
export function useGraphAsk() {
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: { question: string; notebook_id: string; top_k?: number }) =>
      knowledgeGraphApi.ask(data),
    onError: (error) => {
      toast({
        title: t('common.error'),
        description: getApiErrorMessage(error) || 'GraphRAG 问答失败',
        variant: 'destructive',
      })
    },
  })
}

// 从笔记本内容提取知识图谱
export function useExtractGraph() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: ExtractGraphRequest) => knowledgeGraphApi.extract(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.knowledgeGraph(variables.notebook_id),
      })
      toast({
        title: t('common.success'),
        description: '知识图谱提取完成',
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

// 手动添加实体
export function useCreateEntity() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: CreateEntityRequest) => knowledgeGraphApi.createEntity(data),
    onSuccess: (entity) => {
      if (entity.notebook_id) {
        queryClient.invalidateQueries({
          queryKey: QUERY_KEYS.knowledgeGraph(entity.notebook_id),
        })
      }
      toast({
        title: t('common.success'),
        description: '实体创建成功',
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

// 手动添加关系
export function useCreateRelation() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: CreateRelationRequest) =>
      knowledgeGraphApi.createRelation(data),
    onSuccess: () => {
      // 关系可能涉及多个笔记本，统一失效
      queryClient.invalidateQueries({ queryKey: ['knowledge-graph'] })
      toast({
        title: t('common.success'),
        description: '关系创建成功',
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

// 删除实体
export function useDeleteEntity() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (entityId: string) => knowledgeGraphApi.deleteEntity(entityId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-graph'] })
      toast({
        title: t('common.success'),
        description: '实体已删除',
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

// 删除关系
export function useDeleteRelation() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (relationId: string) =>
      knowledgeGraphApi.deleteRelation(relationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-graph'] })
      toast({
        title: t('common.success'),
        description: '关系已删除',
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

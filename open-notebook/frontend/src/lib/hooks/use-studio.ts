// Studio 模块 React Query hooks
// 提供模板管理、报告生成、FAQ 生成、时间线生成的数据获取和变更钩子

import { useQuery, useMutation } from '@tanstack/react-query'
import { studioApi } from '@/lib/api/studio'
import type {
  CreateStudioTemplateRequest,
  UpdateStudioTemplateRequest,
  ReportGenerateRequest,
  FAQGenerateRequest,
  TimelineGenerateRequest,
} from '@/lib/api/studio'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorMessage } from '@/lib/utils/error-handler'

// === Query Keys ===
export const STUDIO_QUERY_KEYS = {
  templates: ['studio', 'templates'] as const,
  template: (id: string) => ['studio', 'templates', id] as const,
}

// === 模板管理 Hooks ===

export function useStudioTemplates() {
  return useQuery({
    queryKey: STUDIO_QUERY_KEYS.templates,
    queryFn: () => studioApi.listTemplates(),
  })
}

export function useStudioTemplate(id: string, enabled: boolean = true) {
  return useQuery({
    queryKey: STUDIO_QUERY_KEYS.template(id),
    queryFn: () => studioApi.getTemplate(id),
    enabled: !!id && enabled,
  })
}

export function useCreateStudioTemplate() {
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: CreateStudioTemplateRequest) => studioApi.createTemplate(data),
    onSuccess: () => {
      toast({
        title: t('common.success'),
        description: t('studio.templateCreateSuccess'),
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t('common.error'),
        description: getApiErrorMessage(error, (key) => t(key)),
        variant: 'destructive',
      })
    },
  })
}

export function useUpdateStudioTemplate() {
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateStudioTemplateRequest }) =>
      studioApi.updateTemplate(id, data),
    onSuccess: () => {
      toast({
        title: t('common.success'),
        description: t('studio.templateUpdateSuccess'),
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t('common.error'),
        description: getApiErrorMessage(error, (key) => t(key)),
        variant: 'destructive',
      })
    },
  })
}

export function useDeleteStudioTemplate() {
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (id: string) => studioApi.deleteTemplate(id),
    onSuccess: () => {
      toast({
        title: t('common.success'),
        description: t('studio.templateDeleteSuccess'),
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t('common.error'),
        description: getApiErrorMessage(error, (key) => t(key)),
        variant: 'destructive',
      })
    },
  })
}

// === 报告生成 Hook ===

export function useGenerateReport() {
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: ReportGenerateRequest) => studioApi.generateReport(data),
    onError: (error: unknown) => {
      toast({
        title: t('common.error'),
        description: getApiErrorMessage(error, (key) => t(key)),
        variant: 'destructive',
      })
    },
  })
}

// === FAQ 生成 Hook ===

export function useGenerateFAQ() {
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: FAQGenerateRequest) => studioApi.generateFAQ(data),
    onError: (error: unknown) => {
      toast({
        title: t('common.error'),
        description: getApiErrorMessage(error, (key) => t(key)),
        variant: 'destructive',
      })
    },
  })
}

// === 时间线生成 Hook ===

export function useGenerateTimeline() {
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: TimelineGenerateRequest) => studioApi.generateTimeline(data),
    onError: (error: unknown) => {
      toast({
        title: t('common.error'),
        description: getApiErrorMessage(error, (key) => t(key)),
        variant: 'destructive',
      })
    },
  })
}

import { useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorKey } from '@/lib/utils/error-handler'
import { searchApi } from '@/lib/api/search'
import { SearchRequest, SemanticSearchRequest } from '@/lib/types/search'

export function useSearch() {
  const { t } = useTranslation()
  return useMutation({
    mutationFn: async (params: SearchRequest) => {
      const response = await searchApi.search(params)

      // Process results to add final_score
      const processedResults = response.results.map(result => ({
        ...result,
        final_score: result.relevance ?? result.similarity ?? result.score ?? 0
      }))

      // Sort by final_score descending
      processedResults.sort((a, b) => b.final_score - a.final_score)

      return {
        ...response,
        results: processedResults
      }
    },
    onError: (error: Error) => {
      toast.error(t('apiErrors.searchFailed'), {
        description: t(getApiErrorKey(error.message))
      })
    }
  })
}

/**
 * 语义搜索 Hook。
 *
 * 使用嵌入向量进行相似度搜索，返回带相关性分数的结果。
 * 结果已按 relevance_score 降序排序。
 */
export function useSemanticSearch() {
  const { t } = useTranslation()
  return useMutation({
    mutationFn: async (params: SemanticSearchRequest) => {
      const response = await searchApi.semanticSearch(params)

      // 按 relevance_score 降序排序
      const sortedResults = [...response.results].sort(
        (a, b) => b.relevance_score - a.relevance_score
      )

      return {
        ...response,
        results: sortedResults,
      }
    },
    onError: (error: Error) => {
      toast.error(t('apiErrors.searchFailed'), {
        description: t(getApiErrorKey(error.message))
      })
    }
  })
}

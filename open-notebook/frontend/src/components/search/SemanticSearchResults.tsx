'use client'

import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { ChevronDown, FileText, StickyNote, Lightbulb, Search } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useModalManager } from '@/lib/hooks/use-modal-manager'
import type { SemanticSearchResultItem } from '@/lib/types/search'

interface SemanticSearchResultsProps {
  /** 语义搜索结果列表 */
  results: SemanticSearchResultItem[]
  /** 结果总数 */
  totalCount: number
  /** 原始查询文本 */
  query: string
}

/**
 * 根据结果类型返回对应的图标和标签。
 */
function getResultTypeMeta(resultType: string | null | undefined) {
  switch (resultType) {
    case 'source':
      return { icon: FileText, label: 'Source' }
    case 'note':
      return { icon: StickyNote, label: 'Note' }
    case 'source_insight':
      return { icon: Lightbulb, label: 'Insight' }
    default:
      return { icon: FileText, label: resultType || 'Item' }
  }
}

/**
 * 将相关性分数（0-1）转换为百分比字符串。
 */
function formatRelevance(score: number): string {
  const percentage = Math.round(score * 100)
  return `${percentage}%`
}

/**
 * 根据相关性分数返回对应的 Badge 变体。
 * - 高相关（>= 0.7）：default（主色）
 * - 中相关（>= 0.4）：secondary
 * - 低相关（< 0.4）：outline
 */
function getRelevanceVariant(
  score: number
): 'default' | 'secondary' | 'outline' {
  if (score >= 0.7) return 'default'
  if (score >= 0.4) return 'secondary'
  return 'outline'
}

/**
 * 语义搜索结果组件。
 *
 * 展示语义搜索返回的结果列表，每条结果包含：
 * - 标题（可点击打开详情弹窗）
 * - 结果类型图标与标签
 * - 相关性分数（百分比形式，带颜色分级）
 * - 内容预览片段（可折叠）
 *
 * 结果按相关性分数降序排列（由 useSemanticSearch hook 保证）。
 */
export function SemanticSearchResults({
  results,
  totalCount,
  query,
}: SemanticSearchResultsProps) {
  const { t } = useTranslation()
  const { openModal } = useModalManager()

  if (totalCount === 0) {
    return (
      <Card>
        <CardContent className="pt-6 text-center text-muted-foreground">
          {t('searchPage.noResultsFor').replace('{query}', query)}
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-3">
      {/* 结果统计 */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium flex items-center gap-2">
          <Search className="h-4 w-4" />
          {t('searchPage.resultsFound').replace(
            '{count}',
            totalCount.toString()
          )}
        </h3>
        <Badge variant="outline">{t('searchPage.vectorSearch')}</Badge>
      </div>

      {/* 结果列表 */}
      <div className="space-y-2 max-h-[60vh] overflow-y-auto pr-2">
        {results.map((result, index) => {
          const { icon: TypeIcon, label: typeLabel } = getResultTypeMeta(
            result.result_type
          )
          // 从 parent_id 解析类型和 ID（格式：source:id / note:id / source_insight:id）
          const parentParts = result.parent_id
            ? result.parent_id.split(':')
            : []
          const itemType = parentParts[0]
          const itemId = parentParts[1]
          const modalType =
            itemType === 'source_insight'
              ? 'insight'
              : (itemType as 'source' | 'note' | 'insight')

          return (
            <Card key={result.id || index}>
              <CardContent className="pt-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    {/* 标题与类型 */}
                    <div className="flex items-center gap-2 flex-wrap">
                      <TypeIcon className="h-4 w-4 text-muted-foreground shrink-0" />
                      {itemId && modalType ? (
                        <button
                          onClick={() => openModal(modalType, itemId)}
                          className="text-primary hover:underline font-medium text-left truncate"
                        >
                          {result.title || t('searchPage.search')}
                        </button>
                      ) : (
                        <span className="font-medium text-left truncate">
                          {result.title || t('searchPage.search')}
                        </span>
                      )}
                      <Badge variant="secondary" className="shrink-0">
                        {typeLabel}
                      </Badge>
                    </div>

                    {/* 相关性分数条 */}
                    <div className="mt-2 flex items-center gap-2">
                      <span className="text-xs text-muted-foreground shrink-0">
                        {t('searchPage.searchType')}
                      </span>
                      <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden max-w-[200px]">
                        <div
                          className="h-full rounded-full bg-primary transition-all"
                          style={{
                            width: `${Math.round(result.relevance_score * 100)}%`,
                          }}
                        />
                      </div>
                      <Badge
                        variant={getRelevanceVariant(result.relevance_score)}
                        className="shrink-0 text-xs"
                      >
                        {formatRelevance(result.relevance_score)}
                      </Badge>
                    </div>

                    {/* 内容预览（可折叠） */}
                    {result.content_preview && (
                      <Collapsible className="mt-3">
                        <CollapsibleTrigger className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
                          <ChevronDown className="h-4 w-4" />
                          {t('searchPage.matches').replace('{count}', '1')}
                        </CollapsibleTrigger>
                        <CollapsibleContent className="mt-2">
                          <div className="text-sm pl-6 py-1 border-l-2 border-muted text-muted-foreground line-clamp-3">
                            {result.content_preview}
                          </div>
                        </CollapsibleContent>
                      </Collapsible>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}

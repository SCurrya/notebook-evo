'use client'

import { useMemo, useState } from 'react'
import { useKnowledgeGraph, useExtractGraph } from '@/lib/hooks/use-knowledge-graph'
import { GraphView } from '@/components/knowledge-graph/GraphView'
import { EntityPanel } from '@/components/knowledge-graph/EntityPanel'
import { Button } from '@/components/ui/button'
import { Network, Sparkles, Loader2 } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import type { GraphEntity } from '@/lib/api/knowledge-graph'

export function NotebookGraph({ notebookId }: { notebookId: string }) {
  const { t } = useTranslation()
  const { data: graph, isLoading } = useKnowledgeGraph(notebookId)
  const extractGraph = useExtractGraph()
  const [selectedEntity, setSelectedEntity] = useState<GraphEntity | null>(null)

  const hasGraph = !!graph && (graph.entities?.length > 0)

  return (
    <div className="flex h-full min-h-[300px] flex-col gap-3">
      {/* 工具栏 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Network className="h-4 w-4" />
          <span>
            {graph?.entities?.length ?? 0} 实体 / {graph?.relations?.length ?? 0} 关系
          </span>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={() => extractGraph.mutate({ notebook_id: notebookId })}
          disabled={extractGraph.isPending}
        >
          {extractGraph.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="h-4 w-4 mr-1" />
          )}
          {t('knowledgeGraph.extract') || '提取图谱'}
        </Button>
      </div>

      {/* 图谱 */}
      {isLoading ? (
        <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
          {t('common.loading') || '加载中...'}
        </div>
      ) : hasGraph ? (
        <div className="flex flex-1 flex-col gap-3 overflow-hidden">
          <div className="min-h-[260px] flex-1 rounded-lg border bg-background">
            <GraphView
              entities={graph!.entities}
              relations={graph!.relations}
              onSelectEntity={(entity) => setSelectedEntity(entity)}
            />
          </div>
          {selectedEntity && (
            <EntityPanel
              entity={selectedEntity}
              entities={graph!.entities}
              relations={graph!.relations}
              onDeleteRelation={() => {}}
              onClose={() => setSelectedEntity(null)}
            />
          )}
        </div>
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 rounded-lg border border-dashed p-6 text-center">
          <Network className="h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">
            {t('knowledgeGraph.empty') || '该笔记本还没有知识图谱'}
          </p>
          <Button
            size="sm"
            variant="outline"
            onClick={() => extractGraph.mutate({ notebook_id: notebookId })}
            disabled={extractGraph.isPending}
          >
            {extractGraph.isPending && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
            {t('knowledgeGraph.extractFromSources') || '从来源提取图谱'}
          </Button>
        </div>
      )}
    </div>
  )
}

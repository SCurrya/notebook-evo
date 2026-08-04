'use client'

// 知识图谱实体详情面板
// 显示选中实体的详细信息，包括属性和相关关系

import { useMemo } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Trash2, X } from 'lucide-react'
import type { GraphEntity, GraphRelation } from '@/lib/api/knowledge-graph'

// 节点类型对应的颜色（与 GraphView 保持一致）
const TYPE_COLORS: Record<string, string> = {
  person: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  organization:
    'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  concept:
    'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  location:
    'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  event: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  other: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-300',
}

function getTypeColorClass(type: string): string {
  return TYPE_COLORS[type.toLowerCase()] || TYPE_COLORS.other
}

interface EntityPanelProps {
  entity: GraphEntity | null
  relations: GraphRelation[]
  entities: GraphEntity[]
  onClose?: () => void
  onDeleteEntity?: (entityId: string) => void
  onDeleteRelation?: (relationId: string) => void
}

export function EntityPanel({
  entity,
  relations,
  entities,
  onClose,
  onDeleteEntity,
  onDeleteRelation,
}: EntityPanelProps) {
  // 实体 ID 到实体的映射
  const entityMap = useMemo(() => {
    const map: Record<string, GraphEntity> = {}
    entities.forEach((e) => {
      map[e.id] = e
    })
    return map
  }, [entities])

  // 与当前实体相关的关系
  const relatedRelations = useMemo(() => {
    if (!entity) return []
    return relations.filter(
      (r) => r.source_id === entity.id || r.target_id === entity.id
    )
  }, [entity, relations])

  if (!entity) {
    return (
      <div className="h-full flex items-center justify-center p-6 text-center">
        <p className="text-sm text-muted-foreground">
          点击图谱中的节点查看实体详情
        </p>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* 头部 */}
      <div className="flex items-start justify-between p-4 border-b">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-base truncate">{entity.name}</h3>
          <Badge
            variant="secondary"
            className={`mt-1 text-[10px] ${getTypeColorClass(entity.type)}`}
          >
            {entity.type}
          </Badge>
        </div>
        <div className="flex items-center gap-1">
          {onDeleteEntity && (
            <Button
              variant="ghost"
              size="sm"
              className="text-destructive hover:text-destructive hover:bg-destructive/10 h-7 w-7 p-0"
              onClick={() => onDeleteEntity(entity.id)}
              title="删除实体"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          )}
          {onClose && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              onClick={onClose}
              title="关闭"
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      </div>

      {/* 内容区 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* 基本信息 */}
        <div className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            基本信息
          </h4>
          <dl className="text-sm space-y-1">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">ID</dt>
              <dd className="font-mono text-xs truncate ml-2 max-w-[60%]">
                {entity.id}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">名称</dt>
              <dd className="font-medium ml-2">{entity.name}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">类型</dt>
              <dd className="font-medium ml-2 capitalize">{entity.type}</dd>
            </div>
          </dl>
        </div>

        {/* 附加属性 */}
        {Object.keys(entity.properties || {}).length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              附加属性
            </h4>
            <dl className="text-sm space-y-1">
              {Object.entries(entity.properties).map(([key, value]) => (
                <div key={key} className="flex justify-between gap-2">
                  <dt className="text-muted-foreground shrink-0">{key}</dt>
                  <dd className="font-medium text-right break-all">
                    {typeof value === 'object'
                      ? JSON.stringify(value)
                      : String(value)}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        )}

        {/* 相关关系 */}
        <div className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            相关关系（{relatedRelations.length}）
          </h4>
          {relatedRelations.length === 0 ? (
            <p className="text-xs text-muted-foreground">暂无相关关系</p>
          ) : (
            <ul className="space-y-1.5">
              {relatedRelations.map((rel) => {
                const isSource = rel.source_id === entity.id
                const otherId = isSource ? rel.target_id : rel.source_id
                const other = entityMap[otherId]
                return (
                  <li
                    key={rel.id}
                    className="flex items-center justify-between gap-2 p-2 rounded border bg-muted/30 text-xs"
                  >
                    <div className="flex items-center gap-1.5 min-w-0 flex-1">
                      <span className="text-muted-foreground shrink-0">
                        {isSource ? '→' : '←'}
                      </span>
                      <span className="font-medium truncate">{rel.type}</span>
                      <span className="text-muted-foreground shrink-0">·</span>
                      <span className="truncate">
                        {other?.name || otherId}
                      </span>
                    </div>
                    {onDeleteRelation && (
                      <button
                        onClick={() => onDeleteRelation(rel.id)}
                        className="text-destructive hover:text-destructive/80 shrink-0"
                        title="删除关系"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    )}
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}

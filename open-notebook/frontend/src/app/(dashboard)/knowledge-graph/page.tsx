'use client'

// 知识图谱页面
// 选择笔记本，查看/提取知识图谱，支持手动添加实体和关系

import { useState } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { PageHeader } from '@/components/ui/page-header'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Network, Sparkles, Plus, Loader2, MessageSquareText } from 'lucide-react'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import {
  useKnowledgeGraph,
  useExtractGraph,
  useCreateEntity,
  useCreateRelation,
  useDeleteEntity,
  useDeleteRelation,
  useGraphAsk,
} from '@/lib/hooks/use-knowledge-graph'
import { GraphView } from '@/components/knowledge-graph/GraphView'
import { EntityPanel } from '@/components/knowledge-graph/EntityPanel'
import type { GraphAskResult, GraphEntity } from '@/lib/api/knowledge-graph'

export default function KnowledgeGraphPage() {
  const [selectedNotebookId, setSelectedNotebookId] = useState<string>('')
  const [selectedEntity, setSelectedEntity] = useState<GraphEntity | null>(null)
  const [addEntityOpen, setAddEntityOpen] = useState(false)
  const [addRelationOpen, setAddRelationOpen] = useState(false)

  // 数据查询
  const { data: notebooks } = useNotebooks(false)
  const {
    data: graphData,
    isLoading: graphLoading,
    isFetching: graphFetching,
  } = useKnowledgeGraph(selectedNotebookId)

  // 变更操作
  const extractGraph = useExtractGraph()
  const createEntity = useCreateEntity()
  const createRelation = useCreateRelation()
  const deleteEntity = useDeleteEntity()
  const deleteRelation = useDeleteRelation()

  // 添加实体表单状态
  const [newEntityName, setNewEntityName] = useState('')
  const [newEntityType, setNewEntityType] = useState('concept')

  // 添加关系表单状态
  const [newRelationSource, setNewRelationSource] = useState('')
  const [newRelationTarget, setNewRelationTarget] = useState('')
  const [newRelationType, setNewRelationType] = useState('')

  // GraphRAG 问答状态
  const [askQuestion, setAskQuestion] = useState('')
  const [askResult, setAskResult] = useState<GraphAskResult | null>(null)
  const graphAsk = useGraphAsk()

  const handleAsk = () => {
    if (!selectedNotebookId || !askQuestion.trim()) return
    graphAsk.mutate(
      { question: askQuestion.trim(), notebook_id: selectedNotebookId, top_k: 5 },
      {
        onSuccess: (data) => {
          setAskResult(data)
        },
      }
    )
  }

  const handleExtract = () => {
    if (!selectedNotebookId) return
    extractGraph.mutate({ notebook_id: selectedNotebookId })
  }

  const handleAddEntity = () => {
    if (!newEntityName.trim() || !selectedNotebookId) return
    createEntity.mutate(
      {
        name: newEntityName.trim(),
        type: newEntityType,
        notebook_id: selectedNotebookId,
      },
      {
        onSuccess: () => {
          setAddEntityOpen(false)
          setNewEntityName('')
          setNewEntityType('concept')
        },
      }
    )
  }

  const handleAddRelation = () => {
    if (!newRelationSource || !newRelationTarget || !newRelationType.trim())
      return
    createRelation.mutate(
      {
        source_id: newRelationSource,
        target_id: newRelationTarget,
        type: newRelationType.trim(),
      },
      {
        onSuccess: () => {
          setAddRelationOpen(false)
          setNewRelationSource('')
          setNewRelationTarget('')
          setNewRelationType('')
        },
      }
    )
  }

  const handleDeleteEntity = (entityId: string) => {
    deleteEntity.mutate(entityId)
    if (selectedEntity?.id === entityId) {
      setSelectedEntity(null)
    }
  }

  const entities = graphData?.entities || []
  const relations = graphData?.relations || []

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto animate-fade-in">
        <PageHeader
          title="知识图谱"
          description="从笔记本内容中提取实体和关系，构建可视化知识图谱"
          icon={Network}
          actions={
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setAddEntityOpen(true)}
                disabled={!selectedNotebookId}
              >
                <Plus className="h-4 w-4 mr-2" />
                添加实体
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setAddRelationOpen(true)}
                disabled={entities.length < 2}
              >
                <Plus className="h-4 w-4 mr-2" />
                添加关系
              </Button>
              <Button
                variant="default"
                size="sm"
                onClick={handleExtract}
                disabled={!selectedNotebookId || extractGraph.isPending}
              >
                {extractGraph.isPending ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4 mr-2" />
                )}
                提取知识图谱
              </Button>
            </div>
          }
          stats={
            <div className="flex gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold">{entities.length}</div>
                <div className="text-xs text-muted-foreground">实体</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">{relations.length}</div>
                <div className="text-xs text-muted-foreground">关系</div>
              </div>
            </div>
          }
        />

        <div className="page-container py-6 space-y-4">
          {/* 笔记本选择器 */}
          <div className="flex items-end gap-3">
            <div className="space-y-1.5 flex-1 max-w-xs">
              <Label htmlFor="notebook-select">选择笔记本</Label>
              <Select
                value={selectedNotebookId}
                onValueChange={(v) => {
                  setSelectedNotebookId(v)
                  setSelectedEntity(null)
                }}
              >
                <SelectTrigger id="notebook-select">
                  <SelectValue placeholder="请选择笔记本" />
                </SelectTrigger>
                <SelectContent>
                  {notebooks?.map((nb) => (
                    <SelectItem key={nb.id} value={nb.id}>
                      {nb.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {graphFetching && (
              <Badge variant="secondary" className="mb-2.5">
                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                同步中
              </Badge>
            )}
          </div>

          {/* GraphRAG 问答面板 */}
          {selectedNotebookId && (
            <div className="research-panel rounded-[24px] p-4 bg-background/70">
              <div className="flex items-center gap-2 mb-2">
                <MessageSquareText className="h-4 w-4 text-primary" />
                <span className="text-sm font-medium">图谱智能问答（GraphRAG）</span>
              </div>
              <div className="flex gap-2">
                <Input
                  value={askQuestion}
                  onChange={(e) => setAskQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleAsk()
                  }}
                  placeholder="输入问题，例如：MCP 是由谁提出的？它和哪些概念相关？"
                  className="flex-1"
                />
                <Button onClick={handleAsk} disabled={graphAsk.isPending || !askQuestion.trim()}>
                  {graphAsk.isPending ? (
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4 mr-1" />
                  )}
                  提问
                </Button>
              </div>
              {graphAsk.isError && (
                <p className="mt-2 text-xs text-destructive">问答失败，请检查模型配置或稍后重试</p>
              )}
              {askResult && (
                <div className="mt-3 space-y-3">
                  <div className="rounded-xl border bg-background/60 p-3">
                    <p className="whitespace-pre-wrap text-sm leading-relaxed">{askResult.answer}</p>
                  </div>
                  {(askResult.entities.length > 0 || askResult.graph_paths.length > 0) && (
                    <details className="rounded-xl border bg-background/60 p-3">
                      <summary className="cursor-pointer text-xs text-muted-foreground">
                        查看图谱推理路径（{askResult.entities.length} 实体 · {askResult.graph_paths.length} 关系）
                      </summary>
                      <div className="mt-2 space-y-1">
                        {askResult.entities.length > 0 && (
                          <p className="text-xs">
                            <span className="text-muted-foreground">匹配实体：</span>
                            {askResult.entities.map((e) => e.name).join('、')}
                          </p>
                        )}
                        {askResult.graph_paths.map((p, i) => (
                          <p key={i} className="font-mono text-xs">
                            {p.source} <span className="text-primary">--[{p.type}]--&gt;</span> {p.target}
                          </p>
                        ))}
                      </div>
                    </details>
                  )}
                </div>
              )}
            </div>
          )}

          {/* 主内容区：图谱 + 详情面板 */}
          {!selectedNotebookId ? (
            <div className="flex items-center justify-center min-h-[400px] research-panel rounded-[24px] bg-background/70">
              <div className="text-center space-y-2">
                <Network className="h-12 w-12 mx-auto text-muted-foreground/50" />
                <p className="text-sm text-muted-foreground">
                  请选择一个笔记本以查看知识图谱
                </p>
              </div>
            </div>
          ) : graphLoading ? (
            <div className="flex items-center justify-center min-h-[400px]">
              <LoadingSpinner size="lg" />
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4 h-[600px]">
              {/* 图谱可视化 */}
              <GraphView
                entities={entities}
                relations={relations}
                onSelectEntity={setSelectedEntity}
                onDeleteEntity={handleDeleteEntity}
                onDeleteRelation={(id) => deleteRelation.mutate(id)}
              />

              {/* 实体详情面板 */}
              <div className="research-panel rounded-[24px] overflow-hidden bg-background/80">
                <EntityPanel
                  entity={selectedEntity}
                  relations={relations}
                  entities={entities}
                  onClose={() => setSelectedEntity(null)}
                  onDeleteEntity={handleDeleteEntity}
                  onDeleteRelation={(id) => deleteRelation.mutate(id)}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 添加实体对话框 */}
      <Dialog open={addEntityOpen} onOpenChange={setAddEntityOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>添加实体</DialogTitle>
            <DialogDescription>
              手动添加一个知识图谱实体
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="entity-name">实体名称</Label>
              <Input
                id="entity-name"
                value={newEntityName}
                onChange={(e) => setNewEntityName(e.target.value)}
                placeholder="例如：张三、Acme 公司、人工智能"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="entity-type">实体类型</Label>
              <Select value={newEntityType} onValueChange={setNewEntityType}>
                <SelectTrigger id="entity-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="person">人物（person）</SelectItem>
                  <SelectItem value="organization">组织（organization）</SelectItem>
                  <SelectItem value="concept">概念（concept）</SelectItem>
                  <SelectItem value="location">地点（location）</SelectItem>
                  <SelectItem value="event">事件（event）</SelectItem>
                  <SelectItem value="other">其他（other）</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddEntityOpen(false)}>
              取消
            </Button>
            <Button
              onClick={handleAddEntity}
              disabled={!newEntityName.trim() || createEntity.isPending}
            >
              {createEntity.isPending && (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              )}
              添加
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 添加关系对话框 */}
      <Dialog open={addRelationOpen} onOpenChange={setAddRelationOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>添加关系</DialogTitle>
            <DialogDescription>
              在两个已存在的实体之间建立关系
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="rel-source">起始实体</Label>
              <Select
                value={newRelationSource}
                onValueChange={setNewRelationSource}
              >
                <SelectTrigger id="rel-source">
                  <SelectValue placeholder="选择起始实体" />
                </SelectTrigger>
                <SelectContent>
                  {entities.map((e) => (
                    <SelectItem key={e.id} value={e.id}>
                      {e.name}（{e.type}）
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="rel-target">目标实体</Label>
              <Select
                value={newRelationTarget}
                onValueChange={setNewRelationTarget}
              >
                <SelectTrigger id="rel-target">
                  <SelectValue placeholder="选择目标实体" />
                </SelectTrigger>
                <SelectContent>
                  {entities.map((e) => (
                    <SelectItem key={e.id} value={e.id}>
                      {e.name}（{e.type}）
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="rel-type">关系类型</Label>
              <Input
                id="rel-type"
                value={newRelationType}
                onChange={(e) => setNewRelationType(e.target.value)}
                placeholder="例如：works_for、located_in、created_by"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddRelationOpen(false)}>
              取消
            </Button>
            <Button
              onClick={handleAddRelation}
              disabled={
                !newRelationSource ||
                !newRelationTarget ||
                !newRelationType.trim() ||
                createRelation.isPending
              }
            >
              {createRelation.isPending && (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              )}
              添加
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppShell>
  )
}

'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Activity,
  BarChart3,
  CheckCircle2,
  ClipboardList,
  Download,
  Loader2,
  Play,
  Trash2,
  XCircle,
} from 'lucide-react'

import { AppShell } from '@/components/layout/AppShell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { PageHeader } from '@/components/ui/page-header'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  deleteEvalReport,
  getEvalReport,
  listEvalReports,
  runEval,
  runSingleEval,
  type EvalMetrics,
  type EvalReport,
  type EvalReportSummary,
} from '@/lib/api/eval'

const METRIC_LABELS: Record<keyof EvalMetrics, string> = {
  faithfulness: '忠实度 (Faithfulness)',
  answer_relevancy: '答案相关性 (Answer Relevancy)',
  context_precision: '上下文精确度 (Context Precision)',
  context_recall: '召回率 (Context Recall)',
}

const METRIC_DESCRIPTIONS: Record<keyof EvalMetrics, string> = {
  faithfulness: '回答是否基于检索到的上下文，而非编造',
  answer_relevancy: '回答是否准确回应用户问题',
  context_precision: '检索到的片段是否与问题相关（排序质量）',
  context_recall: '参考答案所需的信息是否被检索到（召回质量）',
}

function metricColor(value: number): string {
  if (value >= 0.7) return 'text-green-600 dark:text-green-400'
  if (value >= 0.4) return 'text-amber-600 dark:text-amber-400'
  return 'text-red-600 dark:text-red-400'
}

function MetricBar({ label, value, description }: { label: string; value: number; description: string }) {
  const pct = Math.round(value * 100)
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className={`font-mono font-semibold ${metricColor(value)}`}>{pct}%</span>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-gradient-to-r from-primary to-primary/60 transition-all duration-700"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-xs text-muted-foreground">{description}</p>
    </div>
  )
}

function ReportCard({ report, onOpen, onDelete }: {
  report: EvalReportSummary
  onOpen: () => void
  onDelete: () => void
}) {
  const avg = useMemo(() => {
    const a = report.aggregate
    return Object.values(a).reduce((s, v) => s + v, 0) / 4
  }, [report.aggregate])

  return (
    <Card className="cursor-pointer transition-shadow hover:shadow-md" onClick={onOpen}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base">
          评估报告 #{report.id.slice(0, 6)}
        </CardTitle>
        <div className="flex items-center gap-1">
          <Badge variant={avg >= 0.7 ? 'default' : avg >= 0.4 ? 'secondary' : 'destructive'}>
            {Math.round(avg * 100)}分
          </Badge>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-muted-foreground hover:text-destructive"
            onClick={(e) => {
              e.stopPropagation()
              onDelete()
            }}
            aria-label="删除报告"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="pb-4">
        <p className="text-xs text-muted-foreground">
          {report.total_questions} 题 · {new Date(report.created_at).toLocaleString('zh-CN')}
        </p>
      </CardContent>
    </Card>
  )
}

function ReportDetail({ report }: { report: EvalReport }) {
  const items = report.items ?? []

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `eval-report-${report.id}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">评估报告 #{report.id}</h3>
          <p className="text-sm text-muted-foreground">
            {new Date(report.created_at).toLocaleString('zh-CN')} · {report.total_questions} 题
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={handleExport}>
          <Download className="mr-2 h-4 w-4" />
          导出 JSON
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {(Object.keys(METRIC_LABELS) as (keyof EvalMetrics)[]).map((key) => (
          <Card key={key}>
            <CardContent className="pt-6">
              <MetricBar
                label={METRIC_LABELS[key]}
                value={report.aggregate[key] ?? 0}
                description={METRIC_DESCRIPTIONS[key]}
              />
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">逐题明细</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {items.map((item, idx) => {
            const ok = (item.metrics?.faithfulness ?? 0) >= 0.5
            return (
              <div key={idx} className="rounded-lg border p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium">
                      <span className="mr-2 text-muted-foreground">Q{idx + 1}.</span>
                      {item.question}
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">{item.answer}</p>
                  </div>
                  <Badge variant={ok ? 'default' : 'destructive'} className="shrink-0">
                    {ok ? '通过' : '需改进'}
                  </Badge>
                </div>
                <div className="mt-3 grid gap-2 sm:grid-cols-4">
                  {(Object.keys(METRIC_LABELS) as (keyof EvalMetrics)[]).map((key) => (
                    <div key={key} className="rounded-md bg-muted/50 px-2.5 py-1.5 text-xs">
                      <span className="text-muted-foreground">{METRIC_LABELS[key].split(' ')[0]}: </span>
                      <span className={`font-mono font-semibold ${metricColor(item.metrics?.[key] ?? 0)}`}>
                        {Math.round((item.metrics?.[key] ?? 0) * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
                {item.contexts.length > 0 && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs text-muted-foreground">
                      查看检索上下文（{item.contexts.length} 条）
                    </summary>
                    <div className="mt-2 max-h-40 space-y-1 overflow-y-auto rounded-md border p-2">
                      {item.contexts.map((ctx, ci) => (
                        <p key={ci} className="text-xs text-muted-foreground">{ctx.slice(0, 200)}</p>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            )
          })}
        </CardContent>
      </Card>
    </div>
  )
}

export default function EvalPage() {
  const [reports, setReports] = useState<EvalReportSummary[]>([])
  const [selectedReport, setSelectedReport] = useState<EvalReport | null>(null)
  const [running, setRunning] = useState(false)
  const [runningSingle, setRunningSingle] = useState(false)
  const [singleQuestion, setSingleQuestion] = useState('')
  const [singleResult, setSingleResult] = useState<{ answer: string; metrics: EvalMetrics } | null>(null)
  const [topK, setTopK] = useState(5)
  const [error, setError] = useState<string | null>(null)

  const loadReports = useCallback(async () => {
    try {
      setReports(await listEvalReports())
    } catch (e) {
      setError(`加载报告失败: ${e}`)
    }
  }, [])

  useEffect(() => {
    loadReports()
  }, [loadReports])

  const handleRun = async () => {
    setRunning(true)
    setError(null)
    try {
      const report = await runEval(undefined, topK)
      setSelectedReport(report)
      await loadReports()
    } catch (e) {
      setError(`运行评估失败: ${e}`)
    } finally {
      setRunning(false)
    }
  }

  const handleRunSingle = async () => {
    if (!singleQuestion.trim()) return
    setRunningSingle(true)
    setError(null)
    try {
      const result = await runSingleEval(singleQuestion.trim())
      setSingleResult(result)
    } catch (e) {
      setError(`单题评估失败: ${e}`)
    } finally {
      setRunningSingle(false)
    }
  }

  const handleOpenReport = async (id: string) => {
    try {
      setSelectedReport(await getEvalReport(id))
    } catch (e) {
      setError(`加载报告失败: ${e}`)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteEvalReport(id)
      if (selectedReport?.id === id) setSelectedReport(null)
      await loadReports()
    } catch (e) {
      setError(`删除报告失败: ${e}`)
    }
  }

  return (
    <AppShell>
      <div className="container mx-auto max-w-6xl space-y-6 p-6">
        <PageHeader
          title="RAG 评估中心"
          description="对知识库问答质量进行自动评估：忠实度、相关性、上下文精确度与召回率"
          icon={<Activity className="h-5 w-5" />}
        />

        {error && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </div>
        )}

        <Tabs defaultValue="dashboard">
          <TabsList>
            <TabsTrigger value="dashboard">
              <BarChart3 className="mr-2 h-4 w-4" />
              评估概览
            </TabsTrigger>
            <TabsTrigger value="single">
              <ClipboardList className="mr-2 h-4 w-4" />
              单题评估
            </TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">运行完整评估</CardTitle>
                <CardDescription>
                  使用内置测试集（8 个问题）跑一遍完整的 RAG 链路，输出四项质量指标
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap items-end gap-4">
                  <div className="w-40">
                    <Label htmlFor="topk">每题检索片段数 (top-k)</Label>
                    <Input
                      id="topk"
                      type="number"
                      min={1}
                      max={20}
                      value={topK}
                      onChange={(e) => setTopK(Number(e.target.value) || 5)}
                    />
                  </div>
                  <Button onClick={handleRun} disabled={running}>
                    {running ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
                    {running ? '评估运行中…' : '运行完整评估'}
                  </Button>
                </div>
              </CardContent>
            </Card>

            <div className="grid gap-4 md:grid-cols-2">
              {reports.map((r) => (
                <ReportCard key={r.id} report={r} onOpen={() => handleOpenReport(r.id)} onDelete={() => handleDelete(r.id)} />
              ))}
            </div>
            {reports.length === 0 && !running && (
              <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
                暂无评估报告，点击上方按钮开始第一次评估
              </div>
            )}

            {selectedReport && <ReportDetail report={selectedReport} />}
          </TabsContent>

          <TabsContent value="single" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">单题快速评估</CardTitle>
                <CardDescription>输入任意问题，立即评估回答质量</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="question">测试问题</Label>
                  <Input
                    id="question"
                    placeholder="例如：什么是混合检索？它和纯向量检索有什么区别？"
                    value={singleQuestion}
                    onChange={(e) => setSingleQuestion(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleRunSingle()
                    }}
                  />
                </div>
                <Button onClick={handleRunSingle} disabled={runningSingle || !singleQuestion.trim()}>
                  {runningSingle ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
                  {runningSingle ? '评估中…' : '开始评估'}
                </Button>

                {singleResult && (
                  <div className="space-y-4 rounded-lg border p-4">
                    <div className="flex items-center gap-2">
                      {singleResult.metrics.faithfulness >= 0.5 ? (
                        <CheckCircle2 className="h-5 w-5 text-green-600" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-600" />
                      )}
                      <p className="text-sm font-medium">评估结果</p>
                    </div>
                    <p className="text-sm text-muted-foreground">{singleResult.answer}</p>
                    <div className="grid gap-2 sm:grid-cols-4">
                      {(Object.keys(METRIC_LABELS) as (keyof EvalMetrics)[]).map((key) => (
                        <div key={key} className="rounded-md bg-muted/50 px-2.5 py-2 text-xs">
                          <span className="block text-muted-foreground">{METRIC_LABELS[key]}</span>
                          <span className={`font-mono text-base font-semibold ${metricColor(singleResult.metrics[key] ?? 0)}`}>
                            {Math.round((singleResult.metrics[key] ?? 0) * 100)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </AppShell>
  )
}

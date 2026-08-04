﻿'use client'

import { useState } from 'react'
import { Bot, CheckCircle2, Clock, Loader2, Plus, Settings2, Trash2, XCircle, Zap } from 'lucide-react'

import { AppShell } from '@/components/layout/AppShell'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { PageHeader } from '@/components/ui/page-header'
import { Textarea } from '@/components/ui/textarea'
import { useAgentStats, useAgents, useCancelTask, useCreateAgent, useCreateTask, useDeleteAgent, useSetupDefaultAgents, useTasks } from '@/lib/hooks/use-agents'
import type { AgentType, TaskPriority } from '@/lib/types/agents'

const AGENT_TYPE_OPTIONS: { value: AgentType; label: string }[] = [
  { value: 'generic', label: '通用' },
  { value: 'test', label: '测试运行器（pytest）' },
  { value: 'build', label: '构建运行器' },
  { value: 'research', label: '研究员' },
  { value: 'code', label: '开发者' },
  { value: 'review', label: '代码评审' },
]

const PRIORITY_OPTIONS: { value: TaskPriority; label: string }[] = [
  { value: 1, label: '低' },
  { value: 2, label: '普通' },
  { value: 3, label: '高' },
  { value: 4, label: '紧急' },
]

const STATUS_COLORS: Record<string, string> = {
  idle: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300',
  busy: 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
  offline: 'bg-neutral-100 text-neutral-500 dark:bg-neutral-900 dark:text-neutral-500',
  error: 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300',
  pending: 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
  running: 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
  completed: 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300',
  failed: 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300',
  cancelled: 'bg-neutral-100 text-neutral-500 dark:bg-neutral-900 dark:text-neutral-500',
  assigned: 'bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300',
}

function StatCard({ icon: Icon, label, value, color }: { icon: React.ElementType; label: string; value: number | string; color: string }) {
  return (
    <Card className="rounded-2xl">
      <CardContent className="flex items-center gap-3 py-4">
        <div className={`rounded-2xl p-2 ${color}`}><Icon className="h-5 w-5" /></div>
        <div>
          <p className="text-2xl font-semibold">{value}</p>
          <p className="text-xs text-muted-foreground">{label}</p>
        </div>
      </CardContent>
    </Card>
  )
}

export default function AgentsPage() {
  const [showCreateAgent, setShowCreateAgent] = useState(false)
  const [showCreateTask, setShowCreateTask] = useState(false)
  const [newAgentName, setNewAgentName] = useState('')
  const [newAgentType, setNewAgentType] = useState<AgentType>('generic')
  const [newAgentCaps, setNewAgentCaps] = useState('')
  const [newTaskTitle, setNewTaskTitle] = useState('')
  const [newTaskDesc, setNewTaskDesc] = useState('')
  const [newTaskPriority, setNewTaskPriority] = useState<TaskPriority>(2)
  const [newTaskCaps, setNewTaskCaps] = useState('')
  const [newTaskPayload, setNewTaskPayload] = useState('')

  const statsQuery = useAgentStats()
  const agentsQuery = useAgents()
  const tasksQuery = useTasks()
  const createAgent = useCreateAgent()
  const deleteAgent = useDeleteAgent()
  const createTask = useCreateTask()
  const cancelTask = useCancelTask()
  const setupDefaults = useSetupDefaultAgents()

  const handleCreateAgent = async () => {
    if (!newAgentName.trim()) return
    await createAgent.mutateAsync({ name: newAgentName, type: newAgentType, capabilities: newAgentCaps.split(',').map((s) => s.trim()).filter(Boolean) })
    setNewAgentName('')
    setNewAgentCaps('')
    setShowCreateAgent(false)
  }

  const handleCreateTask = async () => {
    if (!newTaskTitle.trim()) return
    let payload = {}
    if (newTaskPayload.trim()) {
      try { payload = JSON.parse(newTaskPayload) } catch { /* ignore parse errors */ }
    }
    await createTask.mutateAsync({ title: newTaskTitle, description: newTaskDesc, priority: newTaskPriority, required_capabilities: newTaskCaps.split(',').map((s) => s.trim()).filter(Boolean), payload })
    setNewTaskTitle('')
    setNewTaskDesc('')
    setNewTaskCaps('')
    setNewTaskPayload('')
    setShowCreateTask(false)
  }

  const stats = statsQuery.data

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto animate-fade-in">
        <PageHeader title="多智能体系统" description="创建和管理 AI 智能体，让它们并行执行任务。" icon={Bot} />

        <div className="page-container py-6 space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard icon={Bot} label="智能体总数" value={stats?.agents.total ?? 0} color="bg-blue-100 text-blue-600 dark:bg-blue-950 dark:text-blue-400" />
            <StatCard icon={Zap} label="进行中任务" value={stats?.tasks.running ?? 0} color="bg-amber-100 text-amber-600 dark:bg-amber-950 dark:text-amber-400" />
            <StatCard icon={CheckCircle2} label="已完成" value={stats?.tasks.completed ?? 0} color="bg-green-100 text-green-600 dark:bg-green-950 dark:text-green-400" />
            <StatCard icon={XCircle} label="失败" value={stats?.tasks.failed ?? 0} color="bg-red-100 text-red-600 dark:bg-red-950 dark:text-red-400" />
          </div>

          {agentsQuery.data?.length === 0 && (
            <Alert className="bg-blue-50 text-blue-900 border-blue-200 dark:bg-blue-950/40 dark:text-blue-200 dark:border-blue-900 rounded-2xl">
              <Settings2 className="h-4 w-4" />
              <AlertTitle>暂无智能体</AlertTitle>
              <AlertDescription className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <span>创建默认智能体（测试、构建、评审、研究）即可快速开始。</span>
                <Button size="sm" onClick={() => setupDefaults.mutate()} disabled={setupDefaults.isPending} className="rounded-xl">
                  {setupDefaults.isPending ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Plus className="h-4 w-4 mr-2" />}
                  初始化默认
                </Button>
              </AlertDescription>
            </Alert>
          )}

          <Card className="research-panel rounded-[24px]">
            <CardHeader className="flex flex-row items-center justify-between gap-3">
              <div>
                <CardTitle>智能体</CardTitle>
                <CardDescription>能力匹配的智能体会自动分配任务。</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={() => setShowCreateAgent(!showCreateAgent)} className="rounded-xl">
                <Plus className="h-4 w-4 mr-2" />新建智能体
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              {showCreateAgent && (
                <div className="rounded-[22px] border p-4 space-y-3 bg-background/70">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <Label className="text-xs">名称</Label>
                      <Input value={newAgentName} onChange={(e) => setNewAgentName(e.target.value)} placeholder="例如：测试运行器" />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">类型</Label>
                      <Select value={newAgentType} onValueChange={(v) => setNewAgentType(v as AgentType)}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>{AGENT_TYPE_OPTIONS.map((opt) => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}</SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">能力（逗号分隔）</Label>
                    <Input value={newAgentCaps} onChange={(e) => setNewAgentCaps(e.target.value)} placeholder="testing, pytest, unit-tests" />
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" size="sm" onClick={() => setShowCreateAgent(false)} className="rounded-xl">取消</Button>
                    <Button size="sm" onClick={handleCreateAgent} disabled={createAgent.isPending || !newAgentName.trim()} className="rounded-xl">
                      {createAgent.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}创建
                    </Button>
                  </div>
                </div>
              )}

              {agentsQuery.data?.length === 0 ? (
                <p className="text-center py-6 text-muted-foreground text-sm">暂无智能体，请新建或点击“初始化默认”。</p>
              ) : (
                <div className="space-y-2">
                  {agentsQuery.data?.map((agent) => (
                    <div key={agent.id} className="flex items-center justify-between rounded-[22px] border p-3 bg-background/80">
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        <div className={`h-2 w-2 rounded-full ${agent.status === 'idle' ? 'bg-green-500' : agent.status === 'busy' ? 'bg-blue-500 animate-pulse' : agent.status === 'error' ? 'bg-red-500' : 'bg-gray-400'}`} />
                        <div className="min-w-0">
                          <p className="font-medium truncate">{agent.name}</p>
                          <p className="text-xs text-muted-foreground">{agent.type} · {agent.capabilities.join(', ') || '无能力标签'}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className={STATUS_COLORS[agent.status]}>{agent.status}</Badge>
                        <Button variant="ghost" size="sm" onClick={() => deleteAgent.mutate(agent.id)} disabled={deleteAgent.isPending || agent.status === 'busy'} className="rounded-full">
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="research-panel rounded-[24px]">
            <CardHeader className="flex flex-row items-center justify-between gap-3">
              <div>
                <CardTitle>任务</CardTitle>
                <CardDescription>任务会自动分配给能力匹配的智能体。</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={() => setShowCreateTask(!showCreateTask)} className="rounded-xl">
                <Plus className="h-4 w-4 mr-2" />新建任务
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              {showCreateTask && (
                <div className="rounded-[22px] border p-4 space-y-3 bg-background/70">
                  <div className="space-y-1">
                    <Label className="text-xs">标题 *</Label>
                    <Input value={newTaskTitle} onChange={(e) => setNewTaskTitle(e.target.value)} placeholder="例如：运行单元测试" />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">描述</Label>
                    <Textarea value={newTaskDesc} onChange={(e) => setNewTaskDesc(e.target.value)} rows={2} placeholder="任务描述..." />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <Label className="text-xs">优先级</Label>
                      <Select value={String(newTaskPriority)} onValueChange={(v) => setNewTaskPriority(Number(v) as TaskPriority)}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>{PRIORITY_OPTIONS.map((opt) => <SelectItem key={opt.value} value={String(opt.value)}>{opt.label}</SelectItem>)}</SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">所需能力</Label>
                      <Input value={newTaskCaps} onChange={(e) => setNewTaskCaps(e.target.value)} placeholder="testing, pytest" />
                    </div>
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">负载（JSON，可选）</Label>
                    <Textarea value={newTaskPayload} onChange={(e) => setNewTaskPayload(e.target.value)} rows={3} placeholder='{"test_path": "tests/", "timeout": 300}' className="font-mono text-xs" />
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" size="sm" onClick={() => setShowCreateTask(false)} className="rounded-xl">取消</Button>
                    <Button size="sm" onClick={handleCreateTask} disabled={createTask.isPending || !newTaskTitle.trim()} className="rounded-xl">
                      {createTask.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}创建任务
                    </Button>
                  </div>
                </div>
              )}

              {tasksQuery.data?.length === 0 ? (
                <p className="text-center py-6 text-muted-foreground text-sm">暂无任务，请在上方创建。</p>
              ) : (
                <div className="space-y-2">
                  {tasksQuery.data?.map((task) => (
                    <div key={task.id} className="rounded-[22px] border p-3 space-y-2 bg-background/80">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          {task.status === 'completed' ? <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" /> : task.status === 'failed' ? <XCircle className="h-4 w-4 text-red-500 shrink-0" /> : task.status === 'running' ? <Loader2 className="h-4 w-4 text-blue-500 animate-spin shrink-0" /> : <Clock className="h-4 w-4 text-muted-foreground shrink-0" />}
                          <span className="font-medium truncate">{task.title}</span>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <Badge variant="outline" className={STATUS_COLORS[task.status]}>{task.status}</Badge>
                          {!['completed', 'failed', 'cancelled'].includes(task.status) && (
                            <Button variant="ghost" size="sm" onClick={() => cancelTask.mutate(task.id)} disabled={cancelTask.isPending} className="rounded-full">取消</Button>
                          )}
                        </div>
                      </div>
                      {task.description && <p className="text-xs text-muted-foreground">{task.description}</p>}
                      {task.status === 'running' && task.progress > 0 && (
                        <div className="w-full bg-muted rounded-full h-1.5"><div className="bg-blue-500 h-1.5 rounded-full transition-all" style={{ width: `${task.progress}%` }} /></div>
                      )}
                      {task.error && <p className="text-xs text-red-500 font-mono">{task.error}</p>}
                      {task.result && (
                        <details className="text-xs">
                          <summary className="cursor-pointer text-muted-foreground">查看结果</summary>
                          <pre className="mt-1 p-2 rounded-2xl bg-muted overflow-auto max-h-40 font-mono">{JSON.stringify(task.result, null, 2)}</pre>
                        </details>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  )
}

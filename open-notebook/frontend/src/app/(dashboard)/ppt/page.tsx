'use client'

import { useState } from 'react'
import {
  CheckCircle2,
  Download,
  Loader2,
  Presentation,
  Trash2,
  XCircle,
} from 'lucide-react'

import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { PageHeader } from '@/components/ui/page-header'
import { Textarea } from '@/components/ui/textarea'
import {
  useCreatePptTask,
  useDeletePptTask,
  usePptTasks,
  usePptTemplates,
} from '@/lib/hooks/use-ppt'
import type { PPTTemplateType } from '@/lib/types/ppt'

const STATE_LABELS: Record<string, { label: string; color: string }> = {
  pending: { label: '等待中', color: 'text-muted-foreground' },
  processing: { label: '生成中', color: 'text-blue-500' },
  completed: { label: '已完成', color: 'text-green-500' },
  failed: { label: '失败', color: 'text-red-500' },
}

const TEMPLATE_ICONS: Record<string, string> = {
  default: '📄',
  business: '💼',
  tech: '⚙️',
  education: '📚',
  creative: '🎨',
}

export default function PptPage() {
  const [title, setTitle] = useState('')
  const [subtitle, setSubtitle] = useState('')
  const [author, setAuthor] = useState('')
  const [markdownContent, setMarkdownContent] = useState('')
  const [selectedTemplate, setSelectedTemplate] =
    useState<PPTTemplateType>('default')

  const templatesQuery = usePptTemplates()
  const tasksQuery = usePptTasks(1, 20)
  const createTask = useCreatePptTask()
  const deleteTask = useDeletePptTask()

  const handleSubmit = async () => {
    if (!title.trim()) return
    await createTask.mutateAsync({
      title: title.trim(),
      subtitle: subtitle.trim() || undefined,
      author: author.trim() || undefined,
      template: selectedTemplate,
      markdown_content: markdownContent.trim() || undefined,
    })
    // 提交后清空表单
    setTitle('')
    setSubtitle('')
    setAuthor('')
    setMarkdownContent('')
  }

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto animate-fade-in">
        <PageHeader
          title="PPT 生成"
          description="从 Markdown 内容生成精美的 PowerPoint 演示文稿，支持多种内置模板。"
          icon={Presentation}
        />

        <div className="page-container py-6 space-y-6">
          {/* 模板选择 */}
          <Card>
            <CardHeader>
              <CardTitle>选择模板</CardTitle>
              <CardDescription>
                选择一种模板风格，每种模板有不同的配色方案和字体。
              </CardDescription>
            </CardHeader>
            <CardContent>
              {templatesQuery.isLoading ? (
                <div className="flex items-center justify-center py-8 text-muted-foreground">
                  <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                  加载模板中...
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
                  {templatesQuery.data?.map((tpl) => {
                    const isSelected = selectedTemplate === tpl.id
                    const gradient = `linear-gradient(135deg, ${tpl.preview_colors[0]} 0%, ${tpl.preview_colors[1]} 50%, ${tpl.preview_colors[2]} 100%)`
                    return (
                      <button
                        key={tpl.id}
                        type="button"
                        onClick={() => setSelectedTemplate(tpl.id)}
                        className={`hover-lift text-left rounded-xl border-2 transition-all duration-normal ease-standard overflow-hidden ${
                          isSelected
                            ? 'border-primary ring-2 ring-primary/20'
                            : 'border-border'
                        }`}
                      >
                        {/* 渐变预览块 */}
                        <div
                          className="h-24 w-full relative"
                          style={{ background: gradient }}
                        >
                          <span className="absolute top-2 right-2 text-2xl">
                            {TEMPLATE_ICONS[tpl.id] ?? '📄'}
                          </span>
                          {isSelected && (
                            <span className="absolute bottom-2 right-2 flex items-center justify-center h-6 w-6 rounded-full bg-primary text-primary-foreground">
                              <CheckCircle2 className="h-4 w-4" />
                            </span>
                          )}
                        </div>
                        {/* 模板信息 */}
                        <div className="p-3 space-y-1">
                          <div className="flex items-center gap-2">
                            <span
                              className="inline-block h-3 w-3 rounded-full"
                              style={{ backgroundColor: tpl.accent_color }}
                            />
                            <span className="font-medium text-sm">
                              {tpl.name}
                            </span>
                          </div>
                          <p className="text-xs text-muted-foreground line-clamp-2">
                            {tpl.description}
                          </p>
                        </div>
                      </button>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          {/* 生成表单 */}
          <Card>
            <CardHeader>
              <CardTitle>新建 PPT 任务</CardTitle>
              <CardDescription>
                填写标题和 Markdown 内容，系统将自动解析为幻灯片。
                使用 <code className="px-1 py-0.5 rounded bg-muted text-xs">## 标题</code> 分隔幻灯片，
                <code className="px-1 py-0.5 rounded bg-muted text-xs">- </code> 添加要点。
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="title">
                  标题 <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="例如：2024 年度工作总结"
                  disabled={createTask.isPending}
                />
              </div>

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="subtitle">副标题</Label>
                  <Input
                    id="subtitle"
                    value={subtitle}
                    onChange={(e) => setSubtitle(e.target.value)}
                    placeholder="例如：回顾与展望"
                    disabled={createTask.isPending}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="author">作者</Label>
                  <Input
                    id="author"
                    value={author}
                    onChange={(e) => setAuthor(e.target.value)}
                    placeholder="例如：张三"
                    disabled={createTask.isPending}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="markdown">Markdown 内容</Label>
                <Textarea
                  id="markdown"
                  value={markdownContent}
                  onChange={(e) => setMarkdownContent(e.target.value)}
                  placeholder={
                    '## 项目概述\n- 项目背景与目标\n- 核心功能介绍\n\n## 技术架构\n- 前端：React + TypeScript\n- 后端：FastAPI + Python\n\n## 成果与展望\n- 已完成核心功能开发\n- 用户反馈积极'
                  }
                  rows={12}
                  className="font-mono text-sm"
                  disabled={createTask.isPending}
                />
                <p className="text-xs text-muted-foreground">
                  提示：每个 <code className="px-1 rounded bg-muted">##</code> 标题会生成一张新幻灯片，
                  其下的 <code className="px-1 rounded bg-muted">-</code> 列表项会作为要点内容。
                </p>
              </div>

              <div className="flex justify-end gap-2">
                <Button
                  onClick={handleSubmit}
                  disabled={createTask.isPending || !title.trim()}
                >
                  {createTask.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      提交中...
                    </>
                  ) : (
                    <>
                      <Presentation className="h-4 w-4 mr-2" />
                      生成 PPT
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* 任务列表 */}
          <Card>
            <CardHeader>
              <CardTitle>PPT 任务</CardTitle>
              <CardDescription>
                跟踪 PPT 生成任务的进度，完成后可下载 .pptx 文件。
              </CardDescription>
            </CardHeader>
            <CardContent>
              {tasksQuery.isLoading ? (
                <div className="flex items-center justify-center py-8 text-muted-foreground">
                  <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                  加载任务中...
                </div>
              ) : tasksQuery.data?.items?.length ? (
                <div className="space-y-3">
                  {tasksQuery.data.items.map((task) => {
                    const stateInfo =
                      STATE_LABELS[task.state] ?? {
                        label: task.state,
                        color: 'text-muted-foreground',
                      }
                    const isActive = !['completed', 'failed'].includes(
                      task.state
                    )
                    return (
                      <div
                        key={task.id}
                        className="flex items-center justify-between rounded-lg border p-4 hover-lift"
                      >
                        <div className="space-y-1 min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            {task.state === 'completed' ? (
                              <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                            ) : task.state === 'failed' ? (
                              <XCircle className="h-4 w-4 text-red-500 shrink-0" />
                            ) : (
                              <Loader2 className="h-4 w-4 text-blue-500 animate-spin shrink-0" />
                            )}
                            <span className="font-medium truncate">
                              {task.title || task.id}
                            </span>
                            <span className={`text-xs ${stateInfo.color}`}>
                              {stateInfo.label}
                              {isActive && task.progress > 0
                                ? ` (${task.progress}%)`
                                : ''}
                            </span>
                            {task.template && (
                              <span className="text-xs text-muted-foreground px-1.5 py-0.5 rounded bg-muted">
                                {task.template}
                              </span>
                            )}
                            {task.slide_count != null && (
                              <span className="text-xs text-muted-foreground">
                                {task.slide_count} 页
                              </span>
                            )}
                          </div>
                          {task.message && (
                            <p className="text-xs text-muted-foreground truncate">
                              {task.message}
                            </p>
                          )}
                          {task.error && (
                            <p className="text-xs text-red-500 truncate">
                              {task.error}
                            </p>
                          )}
                          {task.download_url && task.state === 'completed' && (
                            <a
                              href={task.download_url}
                              className="inline-flex items-center gap-1 text-xs text-blue-500 hover:underline"
                            >
                              <Download className="h-3 w-3" />
                              下载 .pptx 文件
                            </a>
                          )}
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          {task.state === 'completed' && task.download_url && (
                            <Button
                              variant="outline"
                              size="sm"
                              asChild
                            >
                              <a href={task.download_url}>
                                <Download className="h-4 w-4 mr-1" />
                                下载
                              </a>
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => deleteTask.mutate(task.id)}
                            disabled={deleteTask.isPending}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  暂无 PPT 任务，请在上方创建。
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  )
}

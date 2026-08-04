'use client'

// PDF 生成页面
// 使用 reportlab 在服务端直接生成 PDF（无需浏览器打印）
// 支持多种模板：报告、文章、简历、信函、电子书

import { useState } from 'react'
import {
  CheckCircle2,
  Download,
  FileDown,
  FileText,
  Loader2,
  XCircle,
} from 'lucide-react'

import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { PageHeader } from '@/components/ui/page-header'
import { Textarea } from '@/components/ui/textarea'
import { pdfApi } from '@/lib/api/pdf'
import {
  useCreatePdfTask,
  useDeletePdfTask,
  usePdfTasks,
  usePdfTemplates,
} from '@/lib/hooks/use-pdf'
import type { PDFTemplateId } from '@/lib/types/pdf'

// 任务状态展示配置
const STATE_LABELS: Record<string, { label: string; color: string }> = {
  pending: { label: '等待中', color: 'text-muted-foreground' },
  processing: { label: '生成中', color: 'text-blue-500' },
  completed: { label: '已完成', color: 'text-green-500' },
  failed: { label: '失败', color: 'text-red-500' },
}

// 默认 Markdown 示例
const SAMPLE_CONTENT = `## 简介

本文档演示 Open Notebook 的 **PDF 生成** 能力。

核心特性：

- 内置多种专业模板
- 支持 Markdown 解析（*斜体*、**加粗**）
- 中文字体支持（宋体 / 微软雅黑）

## 快速开始

1. 选择一个模板
2. 填写元数据
3. 编写 Markdown 内容
4. 点击"生成 PDF"

## 总结

生成的 PDF 保存在服务端，可随时下载。
`

export default function PdfPage() {
  // 表单状态
  const [template, setTemplate] = useState<PDFTemplateId>('report')
  const [title, setTitle] = useState('')
  const [author, setAuthor] = useState('')
  const [date, setDate] = useState('')
  const [company, setCompany] = useState('')
  const [content, setContent] = useState(SAMPLE_CONTENT)
  const [twoColumn, setTwoColumn] = useState(false)

  // 数据查询与变更
  const templatesQuery = usePdfTemplates()
  const tasksQuery = usePdfTasks(1, 20)
  const createTask = useCreatePdfTask()
  const deleteTask = useDeletePdfTask()

  const templates = templatesQuery.data ?? []

  // 当前选中的模板对象（用于判断是否支持双栏）
  const selectedTemplate = templates.find((t) => t.id === template)
  const supportsTwoColumn = selectedTemplate?.two_column ?? false

  const handleSubmit = async () => {
    if (!title.trim() || !content.trim()) return
    await createTask.mutateAsync({
      template,
      title: title.trim(),
      author: author.trim(),
      date: date.trim(),
      company: company.trim(),
      content,
      two_column: supportsTwoColumn ? twoColumn : false,
    })
  }

  const handleDownload = (taskId: string) => {
    // 在新标签页打开下载链接
    window.open(pdfApi.getDownloadUrl(taskId), '_blank')
  }

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto animate-fade-in">
        <PageHeader
          title="PDF 生成"
          description="使用 reportlab 在服务端生成精美 PDF 文档。选择模板，提供 Markdown 内容，一键下载。"
          icon={FileDown}
        />

        <div className="page-container py-6 space-y-6">
          {/* 模板选择卡片 */}
          <section>
            <h2 className="text-lg font-semibold mb-3">选择模板</h2>
            {templatesQuery.isLoading ? (
              <div className="flex items-center justify-center py-8 text-muted-foreground">
                <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                正在加载模板...
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
                {templates.map((tpl) => {
                  const isSelected = tpl.id === template
                  return (
                    <button
                      key={tpl.id}
                      type="button"
                      onClick={() => {
                        setTemplate(tpl.id)
                        // 切换模板时重置双栏选项
                        if (!tpl.two_column) setTwoColumn(false)
                      }}
                      className={`text-left rounded-xl border p-4 transition-all duration-normal ease-standard hover:elevation-2 ${
                        isSelected
                          ? 'border-primary bg-primary/5 ring-2 ring-primary/30'
                          : 'border-border bg-card hover:border-primary/40'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <FileText
                          className={`h-5 w-5 ${
                            isSelected ? 'text-primary' : 'text-muted-foreground'
                          }`}
                        />
                        {isSelected && (
                          <CheckCircle2 className="h-4 w-4 text-primary" />
                        )}
                      </div>
                      <h3 className="font-medium text-sm mb-1">{tpl.name}</h3>
                      <p className="text-xs text-muted-foreground line-clamp-3">
                        {tpl.description}
                      </p>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {tpl.has_cover && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                            封面
                          </span>
                        )}
                        {tpl.has_toc && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                            目录
                          </span>
                        )}
                        {tpl.two_column && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                            双栏
                          </span>
                        )}
                        {tpl.has_header_footer && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                            页眉/页脚
                          </span>
                        )}
                      </div>
                    </button>
                  )
                })}
              </div>
            )}
          </section>

          {/* 生成表单 */}
          <Card className="research-panel rounded-[24px]">
            <CardHeader>
              <CardTitle>新建 PDF 文档</CardTitle>
              <CardDescription>
                填写元数据和 Markdown 内容。PDF 在服务端使用 reportlab 生成。
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="title">标题（必填）</Label>
                <Input
                  id="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="例如：2026 年第二季度业务报告"
                  disabled={createTask.isPending}
                />
              </div>

              <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="author">作者</Label>
                  <Input
                    id="author"
                    value={author}
                    onChange={(e) => setAuthor(e.target.value)}
                    placeholder="张三"
                    disabled={createTask.isPending}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="date">日期</Label>
                  <Input
                    id="date"
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    placeholder="2026-06-21"
                    disabled={createTask.isPending}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="company">公司</Label>
                  <Input
                    id="company"
                    value={company}
                    onChange={(e) => setCompany(e.target.value)}
                    placeholder="某科技公司"
                    disabled={createTask.isPending}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="content">Markdown 内容（必填）</Label>
                <Textarea
                  id="content"
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="## 章节&#10;&#10;用 Markdown 编写内容..."
                  rows={12}
                  className="font-mono text-xs"
                  disabled={createTask.isPending}
                />
                <p className="text-xs text-muted-foreground">
                  支持：<code className="px-1 rounded bg-muted">#</code>{' '}
                  标题、
                  <code className="px-1 rounded bg-muted">-</code> 无序列表、
                  <code className="px-1 rounded bg-muted">1.</code> 有序列表、
                  <code className="px-1 rounded bg-muted">**加粗**</code>、
                  <code className="px-1 rounded bg-muted">*斜体*</code>、
                  <code className="px-1 rounded bg-muted">`代码`</code>
                </p>
              </div>

              {/* 双栏选项（仅 article 模板） */}
              {supportsTwoColumn && (
                <div className="flex items-center gap-2">
                  <input
                    id="two-column"
                    type="checkbox"
                    checked={twoColumn}
                    onChange={(e) => setTwoColumn(e.target.checked)}
                    disabled={createTask.isPending}
                    className="h-4 w-4 rounded border-input"
                  />
                  <Label htmlFor="two-column" className="cursor-pointer">
                    双栏布局（学术风格）
                  </Label>
                </div>
              )}

              <div className="flex justify-end gap-2">
                <Button
                  onClick={handleSubmit}
                  disabled={
                    createTask.isPending || !title.trim() || !content.trim()
                  }
                >
                  {createTask.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      正在生成...
                    </>
                  ) : (
                    <>
                      <FileDown className="h-4 w-4 mr-2" />
                      生成 PDF
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* 任务列表 */}
          <Card className="research-panel rounded-[24px]">
            <CardHeader>
              <CardTitle>PDF 任务</CardTitle>
              <CardDescription>
                跟踪生成进度，下载已完成的 PDF。
              </CardDescription>
            </CardHeader>
            <CardContent>
              {tasksQuery.isLoading ? (
                <div className="flex items-center justify-center py-8 text-muted-foreground">
                  <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                  正在加载任务...
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
                        className="flex items-center justify-between rounded-lg border p-4"
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
                            <span className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                              {task.template}
                            </span>
                            <span className={`text-xs ${stateInfo.color}`}>
                              {stateInfo.label}
                              {isActive && task.progress > 0
                                ? ` (${task.progress}%)`
                                : ''}
                            </span>
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
                          {task.file_size != null && task.state === 'completed' && (
                            <p className="text-xs text-muted-foreground">
                              {(task.file_size / 1024).toFixed(1)} KB
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          {task.state === 'completed' && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleDownload(task.id)}
                            >
                              <Download className="h-4 w-4 mr-1" />
                              下载
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => deleteTask.mutate(task.id)}
                            disabled={deleteTask.isPending}
                          >
                            删除
                          </Button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  暂无 PDF 任务，请在上方创建。
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  )
}

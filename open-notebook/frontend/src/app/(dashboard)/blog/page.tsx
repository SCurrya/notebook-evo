'use client'

/**
 * 博客创作页面
 *
 * 左侧：文章列表（支持搜索、按状态过滤）
 * 右侧：编辑器（Markdown 编辑 + HTML 实时预览，分屏）
 * 顶部工具栏：新建、保存、发布/取消发布、导出
 */

import { useMemo, useState } from 'react'
import {
  Download,
  Edit,
  Eye,
  FileText,
  Loader2,
  Plus,
  Save,
  Search,
  Send,
  Trash2,
} from 'lucide-react'

import { AppShell } from '@/components/layout/AppShell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { PageHeader } from '@/components/ui/page-header'
import { Textarea } from '@/components/ui/textarea'
import {
  useBlogPosts,
  useCreateBlogPost,
  useDeleteBlogPost,
  useExportBlogPost,
  usePublishBlogPost,
  useUpdateBlogPost,
} from '@/lib/hooks/use-blog'
import type {
  BlogExportFormat,
  BlogPostResponse,
  BlogPostStatus,
} from '@/lib/types/blog'

/** 状态标签样式映射 */
const STATUS_BADGE: Record<
  BlogPostStatus,
  { label: string; variant: 'default' | 'secondary' | 'outline' }
> = {
  draft: { label: '草稿', variant: 'secondary' },
  published: { label: '已发布', variant: 'default' },
}

/** 状态过滤选项 */
const STATUS_FILTERS: { value: BlogPostStatus | 'all'; label: string }[] = [
  { value: 'all', label: '全部' },
  { value: 'draft', label: '草稿' },
  { value: 'published', label: '已发布' },
]

/** 编辑器表单状态 */
interface EditorState {
  id: string | null
  title: string
  content: string
  tags: string
  category: string
  author: string
  status: BlogPostStatus
}

const EMPTY_EDITOR: EditorState = {
  id: null,
  title: '',
  content: '',
  tags: '',
  category: '',
  author: '',
  status: 'draft',
}

export default function BlogPage() {
  // 列表查询参数
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<BlogPostStatus | 'all'>(
    'all'
  )

  // 当前编辑的文章
  const [editor, setEditor] = useState<EditorState>(EMPTY_EDITOR)
  const [isDirty, setIsDirty] = useState(false)

  // 列表查询（搜索词去抖：本地即时过滤已加载列表，避免频繁请求）
  const postsQuery = useBlogPosts({
    page: 1,
    page_size: 100,
    status: statusFilter === 'all' ? undefined : statusFilter,
    search: search.trim() || undefined,
  })
  const createPost = useCreateBlogPost()
  const updatePost = useUpdateBlogPost()
  const deletePost = useDeleteBlogPost()
  const publishPost = usePublishBlogPost()
  const exportPost = useExportBlogPost()

  const posts = postsQuery.data?.items ?? []

  // 选中文章时同步到编辑器
  const handleSelectPost = (post: BlogPostResponse) => {
    setEditor({
      id: post.id,
      title: post.title,
      content: post.content,
      tags: post.tags.join(', '),
      category: post.category ?? '',
      author: post.author ?? '',
      status: post.status,
    })
    setIsDirty(false)
  }

  // 新建空白文章
  const handleNewPost = () => {
    setEditor(EMPTY_EDITOR)
    setIsDirty(false)
  }

  // 编辑器字段更新
  const updateField = <K extends keyof EditorState>(
    key: K,
    value: EditorState[K]
  ) => {
    setEditor((prev) => ({ ...prev, [key]: value }))
    setIsDirty(true)
  }

  // 保存文章（新建或更新）
  const handleSave = async () => {
    if (!editor.title.trim()) return
    const tags = editor.tags
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean)

    if (editor.id) {
      await updatePost.mutateAsync({
        postId: editor.id,
        request: {
          title: editor.title,
          content: editor.content,
          tags,
          category: editor.category || null,
          author: editor.author || null,
        },
      })
    } else {
      const created = await createPost.mutateAsync({
        title: editor.title,
        content: editor.content,
        tags,
        category: editor.category || undefined,
        author: editor.author || undefined,
      })
      setEditor((prev) => ({ ...prev, id: created.id, status: created.status }))
    }
    setIsDirty(false)
  }

  // 发布/取消发布
  const handleTogglePublish = async () => {
    if (!editor.id) return
    const next: BlogPostStatus =
      editor.status === 'published' ? 'draft' : 'published'
    const updated = await publishPost.mutateAsync({
      postId: editor.id,
      status: next,
    })
    updateField('status', updated.status)
  }

  // 删除当前文章
  const handleDelete = async () => {
    if (!editor.id) return
    await deletePost.mutateAsync(editor.id)
    handleNewPost()
  }

  // 导出文章
  const handleExport = async (format: BlogExportFormat) => {
    if (!editor.id) return
    await exportPost.mutateAsync({ postId: editor.id, format })
  }

  const isEditingExisting = editor.id !== null
  const canSave = editor.title.trim().length > 0 && isDirty
  const canPublish = isEditingExisting
  const canExport = isEditingExisting
  const canDelete = isEditingExisting

  return (
    <AppShell>
      <div className="flex-1 overflow-hidden flex flex-col animate-fade-in">
        <PageHeader
          title="博客创作"
          description="使用 Markdown 撰写博客文章，实时预览，一键发布与导出。"
          icon={FileText}
          actions={
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={handleNewPost}
              >
                <Plus className="h-4 w-4" />
                新建
              </Button>
              <Button
                size="sm"
                onClick={handleSave}
                disabled={!canSave || createPost.isPending || updatePost.isPending}
              >
                {updatePost.isPending || createPost.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                保存
              </Button>
              <Button
                variant="gradient"
                size="sm"
                onClick={handleTogglePublish}
                disabled={!canPublish || publishPost.isPending}
              >
                {publishPost.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : editor.status === 'published' ? (
                  <Eye className="h-4 w-4" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
                {editor.status === 'published' ? '取消发布' : '发布'}
              </Button>
            </>
          }
        />

        <div className="flex-1 grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-0 min-h-0 overflow-hidden">
          {/* 左侧：文章列表 */}
          <aside className="flex flex-col border-r border-border/50 min-h-0 overflow-hidden bg-background/35">
            <div className="p-4 space-y-3 border-b border-border/50">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="搜索标题或内容..."
                  className="pl-8"
                />
              </div>
              <div className="flex gap-1.5">
                {STATUS_FILTERS.map((opt) => (
                  <Button
                    key={opt.value}
                    size="sm"
                    variant={
                      statusFilter === opt.value ? 'default' : 'outline'
                    }
                    className="h-7 px-2.5 text-xs"
                    onClick={() => setStatusFilter(opt.value)}
                  >
                    {opt.label}
                  </Button>
                ))}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto">
              {postsQuery.isLoading ? (
                <div className="flex items-center justify-center py-8 text-muted-foreground text-sm">
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  加载中...
                </div>
              ) : posts.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground text-sm">
                  <FileText className="h-8 w-8 mx-auto mb-2 opacity-40" />
                  暂无文章
                </div>
              ) : (
                <ul className="divide-y divide-border/40">
                  {posts.map((post) => {
                    const isActive = editor.id === post.id
                    return (
                      <li key={post.id}>
                        <button
                          onClick={() => handleSelectPost(post)}
                          className={`w-full text-left px-4 py-3 transition-colors hover:bg-accent/50 ${
                            isActive ? 'bg-accent/70' : ''
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <h3 className="font-medium text-sm line-clamp-1 flex-1">
                              {post.title}
                            </h3>
                            <Badge
                              variant={STATUS_BADGE[post.status].variant}
                              className="shrink-0 text-[10px]"
                            >
                              {STATUS_BADGE[post.status].label}
                            </Badge>
                          </div>
                          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                            {post.content || '（无内容）'}
                          </p>
                          <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                            {post.category && (
                              <Badge variant="outline" className="text-[10px]">
                                {post.category}
                              </Badge>
                            )}
                            {post.tags.slice(0, 3).map((tag) => (
                              <Badge
                                key={tag}
                                variant="secondary"
                                className="text-[10px]"
                              >
                                #{tag}
                              </Badge>
                            ))}
                          </div>
                          <p className="text-[10px] text-muted-foreground/70 mt-1.5">
                            {post.updated_at.slice(0, 10)}
                          </p>
                        </button>
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>
          </aside>

          {/* 右侧：编辑器 + 预览 */}
          <section className="flex flex-col min-h-0 overflow-hidden">
            {/* 工具栏 */}
            <div className="flex items-center justify-between gap-2 px-4 py-2.5 border-b border-border/50 bg-background/65 backdrop-blur-sm">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Edit className="h-4 w-4" />
                <span>
                  {isEditingExisting ? '编辑文章' : '新建文章'}
                  {isDirty && <span className="text-amber-500 ml-1">•</span>}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="flex rounded-md border overflow-hidden">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="rounded-none h-8 px-3 text-xs"
                    onClick={() => handleExport('md')}
                    disabled={!canExport || exportPost.isPending}
                  >
                    <Download className="h-3.5 w-3.5" />
                    .md
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="rounded-none h-8 px-3 text-xs border-l"
                    onClick={() => handleExport('html')}
                    disabled={!canExport || exportPost.isPending}
                  >
                    <Download className="h-3.5 w-3.5" />
                    .html
                  </Button>
                </div>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={handleDelete}
                  disabled={!canDelete || deletePost.isPending}
                  title="删除文章"
                >
                  {deletePost.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Trash2 className="h-4 w-4 text-destructive" />
                  )}
                </Button>
              </div>
            </div>

            {/* 编辑区 */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="title">标题 *</Label>
                  <Input
                    id="title"
                    value={editor.title}
                    onChange={(e) => updateField('title', e.target.value)}
                    placeholder="输入文章标题..."
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="category">分类</Label>
                  <Input
                    id="category"
                    value={editor.category}
                    onChange={(e) => updateField('category', e.target.value)}
                    placeholder="例如：技术随笔"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tags">标签（逗号分隔）</Label>
                  <Input
                    id="tags"
                    value={editor.tags}
                    onChange={(e) => updateField('tags', e.target.value)}
                    placeholder="例如：React, 前端, 教程"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="author">作者</Label>
                  <Input
                    id="author"
                    value={editor.author}
                    onChange={(e) => updateField('author', e.target.value)}
                    placeholder="作者名称"
                  />
                </div>
              </div>

              {/* Markdown 编辑 + HTML 预览 分屏 */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 min-h-[420px]">
                <Card className="research-panel flex flex-col min-h-0">
                  <CardContent className="flex flex-col flex-1 min-h-0 p-4">
                    <div className="flex items-center justify-between mb-2">
                      <Label htmlFor="content" className="text-xs uppercase tracking-wide text-muted-foreground">
                        Markdown 编辑
                      </Label>
                      <span className="text-[10px] text-muted-foreground">
                        {editor.content.length} 字符
                      </span>
                    </div>
                    <Textarea
                      id="content"
                      value={editor.content}
                      onChange={(e) => updateField('content', e.target.value)}
                      placeholder={'# 标题\n\n在这里用 Markdown 撰写正文...\n\n- 列表项\n- **加粗**、*斜体*、`代码`\n\n```python\nprint("hello")\n```'}
                      className="flex-1 min-h-[360px] resize-none font-mono text-sm leading-relaxed"
                    />
                  </CardContent>
                </Card>

                <Card className="research-panel flex flex-col min-h-0">
                  <CardContent className="flex flex-col flex-1 min-h-0 p-4">
                    <div className="flex items-center justify-between mb-2">
                      <Label className="text-xs uppercase tracking-wide text-muted-foreground">
                        HTML 预览
                      </Label>
                      <Eye className="h-3.5 w-3.5 text-muted-foreground" />
                    </div>
                    <PreviewContent content={editor.content} />
                  </CardContent>
                </Card>
              </div>
            </div>
          </section>
        </div>
      </div>
    </AppShell>
  )
}

/**
 * 预览内容组件。
 *
 * 由于编辑器中的 Markdown 是纯文本，前端仅做轻量预览：
 * 优先展示已保存文章的 html（由后端渲染），否则展示纯文本占位。
 * 这里使用 dangerouslySetInnerHTML 渲染后端返回的 HTML。
 */
function PreviewContent({ content }: { content: string }) {
  // 纯前端轻量预览：将 Markdown 文本做最简单的转换用于即时反馈
  // 真正的 HTML 渲染发生在保存后从后端读取 post.html 字段
  const previewHtml = useMemo(() => renderLightweightMarkdown(content), [content])

  if (!content.trim()) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
        预览区为空
      </div>
    )
  }

  return (
    <div
      className="flex-1 overflow-y-auto prose prose-sm dark:prose-invert max-w-none rounded-md border border-border/40 p-4 bg-background/40"
      dangerouslySetInnerHTML={{ __html: previewHtml }}
    />
  )
}

/**
 * 轻量级 Markdown 渲染（仅用于编辑时即时预览）。
 *
 * 后端保存时会用 Python markdown 库做完整渲染；
 * 这里只做最基本的语法转换以提供即时反馈。
 */
function renderLightweightMarkdown(text: string): string {
  // 先转义 HTML 特殊字符，防止 XSS
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  return (
    escaped
      // 标题
      .replace(/^### (.+)$/gm, '<h3>$1</h3>')
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
      .replace(/^# (.+)$/gm, '<h1>$1</h1>')
      // 加粗、斜体、行内代码
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      // 无序列表
      .replace(/^- (.+)$/gm, '<li>$1</li>')
      // 段落（连续非空行，且非块级元素）
      .split(/\n\n+/)
      .map((block) => {
        if (/^<(h\d|ul|ol|li|pre|blockquote)/.test(block.trim())) {
          return block
        }
        if (block.trim() === '') return ''
        return `<p>${block.replace(/\n/g, '<br>')}</p>`
      })
      .join('\n')
      // 将连续 <li> 包裹为 <ul>
      .replace(/(?:<li>.*<\/li>\n?)+/g, (match) => `<ul>${match}</ul>`)
  )
}

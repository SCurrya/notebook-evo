'use client'

// 共享笔记本只读视图
// 通过 token 访问的笔记本只读视图，显示笔记本的源和笔记列表

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { FileText, StickyNote, BookOpen, Lock } from 'lucide-react'
import { useSharedNotebook } from '@/lib/hooks/use-share'
import type { SharePermission } from '@/lib/api/share'

// 权限级别显示
const PERMISSION_LABELS: Record<SharePermission, string> = {
  READ_ONLY: '只读',
  COMMENT: '可评论',
  EDIT: '可编辑',
}

// 权限级别颜色
const PERMISSION_COLORS: Record<SharePermission, string> = {
  READ_ONLY: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  COMMENT: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  EDIT: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
}

interface SharedNotebookViewProps {
  token: string
}

export function SharedNotebookView({ token }: SharedNotebookViewProps) {
  const { data: notebook, isLoading, error } = useSharedNotebook(token)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px] p-6">
        <Card className="max-w-md w-full">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <Lock className="h-5 w-5" />
              访问失败
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {error.response?.status === 404
                ? '共享链接不存在或已被撤销'
                : error.response?.status === 410
                ? '共享链接已过期'
                : '无法访问此共享笔记本，请检查链接是否正确'}
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!notebook) return null

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-4xl mx-auto p-6 space-y-6">
        {/* 头部 */}
        <div className="space-y-2 pb-4 border-b">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <BookOpen className="h-3.5 w-3.5" />
            <span>共享笔记本</span>
            <Badge
              variant="secondary"
              className={`text-[10px] ${PERMISSION_COLORS[notebook.permissions]}`}
            >
              {PERMISSION_LABELS[notebook.permissions] || notebook.permissions}
            </Badge>
          </div>
          <h1 className="text-2xl font-bold">{notebook.notebook_name}</h1>
          {notebook.notebook_description && (
            <p className="text-muted-foreground">
              {notebook.notebook_description}
            </p>
          )}
        </div>

        {/* 统计信息 */}
        <div className="grid grid-cols-2 gap-4">
          <Card>
            <CardContent className="flex items-center gap-3 p-4">
              <FileText className="h-8 w-8 text-blue-500" />
              <div>
                <div className="text-2xl font-bold">
                  {notebook.sources.length}
                </div>
                <div className="text-xs text-muted-foreground">源</div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-3 p-4">
              <StickyNote className="h-8 w-8 text-amber-500" />
              <div>
                <div className="text-2xl font-bold">{notebook.notes.length}</div>
                <div className="text-xs text-muted-foreground">笔记</div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 源列表 */}
        <div className="space-y-3">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <FileText className="h-5 w-5" />
            源（{notebook.sources.length}）
          </h2>
          {notebook.sources.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4">暂无源</p>
          ) : (
            <ul className="space-y-2">
              {notebook.sources.map((source) => (
                <li
                  key={source.id}
                  className="flex items-center justify-between p-3 rounded border bg-card"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                    <span className="text-sm font-medium truncate">
                      {source.title || '未命名源'}
                    </span>
                  </div>
                  <span className="text-xs text-muted-foreground shrink-0 ml-2">
                    {source.updated
                      ? new Date(source.updated).toLocaleDateString()
                      : ''}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* 笔记列表 */}
        <div className="space-y-3">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <StickyNote className="h-5 w-5" />
            笔记（{notebook.notes.length}）
          </h2>
          {notebook.notes.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4">暂无笔记</p>
          ) : (
            <ul className="space-y-2">
              {notebook.notes.map((note) => (
                <li
                  key={note.id}
                  className="flex items-center justify-between p-3 rounded border bg-card"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <StickyNote className="h-4 w-4 text-muted-foreground shrink-0" />
                    <span className="text-sm font-medium truncate">
                      {note.title || '未命名笔记'}
                    </span>
                  </div>
                  <span className="text-xs text-muted-foreground shrink-0 ml-2">
                    {note.updated
                      ? new Date(note.updated).toLocaleDateString()
                      : ''}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* 底部提示 */}
        <div className="text-center text-xs text-muted-foreground pt-4 border-t">
          此为共享只读视图 · 由 Open Notebook 提供
        </div>
      </div>
    </div>
  )
}

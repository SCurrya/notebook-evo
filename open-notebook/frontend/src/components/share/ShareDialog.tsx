'use client'

// 共享对话框组件
// 用于创建共享链接、查看现有链接、撤销链接

import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Loader2, Copy, Check, Trash2, Link as LinkIcon, Share2 } from 'lucide-react'
import { useShareLinks, useCreateShareLink, useRevokeShareLink } from '@/lib/hooks/use-share'
import type { SharePermission } from '@/lib/api/share'

interface ShareDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  notebookId: string
  notebookName: string
}

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

export function ShareDialog({
  open,
  onOpenChange,
  notebookId,
  notebookName,
}: ShareDialogProps) {
  const { data: links, isLoading: linksLoading } = useShareLinks(notebookId)
  const createShareLink = useCreateShareLink()
  const revokeShareLink = useRevokeShareLink()

  // 新建链接表单状态
  const [permission, setPermission] = useState<SharePermission>('READ_ONLY')
  const [expiresAt, setExpiresAt] = useState('')
  const [copiedToken, setCopiedToken] = useState<string | null>(null)

  // 重置表单
  useEffect(() => {
    if (open) {
      setPermission('READ_ONLY')
      setExpiresAt('')
      setCopiedToken(null)
    }
  }, [open])

  // 构建共享 URL
  const buildShareUrl = (token: string) => {
    if (typeof window !== 'undefined') {
      return `${window.location.origin}/shared/${token}`
    }
    return `/shared/${token}`
  }

  // 复制链接到剪贴板
  const handleCopy = async (token: string) => {
    const url = buildShareUrl(token)
    try {
      await navigator.clipboard.writeText(url)
      setCopiedToken(token)
      setTimeout(() => setCopiedToken(null), 2000)
    } catch (err) {
      console.error('复制失败:', err)
    }
  }

  // 创建共享链接
  const handleCreate = () => {
    createShareLink.mutate({
      notebookId,
      data: {
        permissions: permission,
        expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
      },
    })
  }

  // 撤销共享链接
  const handleRevoke = (linkId: string) => {
    if (window.confirm('确定要撤销此共享链接吗？撤销后无法恢复。')) {
      revokeShareLink.mutate(linkId)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Share2 className="h-5 w-5" />
            共享笔记本
          </DialogTitle>
          <DialogDescription>
            为「{notebookName}」创建共享链接，允许他人通过链接访问
          </DialogDescription>
        </DialogHeader>

        {/* 创建新链接 */}
        <div className="space-y-3 py-2 border-b">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="share-permission" className="text-xs">
                权限级别
              </Label>
              <Select
                value={permission}
                onValueChange={(v) => setPermission(v as SharePermission)}
              >
                <SelectTrigger id="share-permission">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="READ_ONLY">只读</SelectItem>
                  <SelectItem value="COMMENT">可评论</SelectItem>
                  <SelectItem value="EDIT">可编辑</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="share-expires" className="text-xs">
                过期时间（可选）
              </Label>
              <Input
                id="share-expires"
                type="datetime-local"
                value={expiresAt}
                onChange={(e) => setExpiresAt(e.target.value)}
              />
            </div>
          </div>
          <Button
            onClick={handleCreate}
            disabled={createShareLink.isPending}
            className="w-full"
            size="sm"
          >
            {createShareLink.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <LinkIcon className="h-4 w-4 mr-2" />
            )}
            创建共享链接
          </Button>
        </div>

        {/* 现有链接列表 */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-xs">现有共享链接</Label>
            {links && links.length > 0 && (
              <Badge variant="secondary" className="text-[10px]">
                {links.length} 个
              </Badge>
            )}
          </div>

          {linksLoading ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : !links || links.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-6">
              暂无共享链接
            </p>
          ) : (
            <ul className="space-y-2 max-h-60 overflow-y-auto">
              {links.map((link) => (
                <li
                  key={link.id}
                  className="flex items-center gap-2 p-2 rounded border bg-muted/30"
                >
                  <Badge
                    variant="secondary"
                    className={`text-[10px] shrink-0 ${PERMISSION_COLORS[link.permissions]}`}
                  >
                    {PERMISSION_LABELS[link.permissions] || link.permissions}
                  </Badge>
                  <code className="text-xs flex-1 truncate font-mono">
                    {buildShareUrl(link.token)}
                  </code>
                  {link.expires_at && (
                    <span className="text-[10px] text-muted-foreground shrink-0">
                      {new Date(link.expires_at).toLocaleDateString()}
                    </span>
                  )}
                  <button
                    onClick={() => handleCopy(link.token)}
                    className="shrink-0 p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground"
                    title="复制链接"
                  >
                    {copiedToken === link.token ? (
                      <Check className="h-3.5 w-3.5 text-emerald-500" />
                    ) : (
                      <Copy className="h-3.5 w-3.5" />
                    )}
                  </button>
                  <button
                    onClick={() => handleRevoke(link.id)}
                    className="shrink-0 p-1 rounded hover:bg-destructive/10 text-destructive"
                    title="撤销链接"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            关闭
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

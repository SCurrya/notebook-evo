'use client'

// API Key 创建对话框
// 创建新的 API Key，并在创建成功后显示明文（仅此一次）

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
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Copy, Check, AlertTriangle, KeyRound } from 'lucide-react'
import { useCreateApiKey } from '@/lib/hooks/use-api-keys'

interface ApiKeyDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

// 可选权限
const AVAILABLE_PERMISSIONS = ['read', 'write'] as const

export function ApiKeyDialog({ open, onOpenChange }: ApiKeyDialogProps) {
  const createApiKey = useCreateApiKey()

  // 表单状态
  const [name, setName] = useState('')
  const [permissions, setPermissions] = useState<string[]>(['read'])

  // 创建结果（明文 key）
  const [createdKey, setCreatedKey] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  // 重置表单
  useEffect(() => {
    if (open) {
      setName('')
      setPermissions(['read'])
      setCreatedKey(null)
      setCopied(false)
    }
  }, [open])

  // 切换权限
  const togglePermission = (perm: string) => {
    setPermissions((prev) =>
      prev.includes(perm) ? prev.filter((p) => p !== perm) : [...prev, perm]
    )
  }

  // 创建 API Key
  const handleCreate = () => {
    if (!name.trim()) return
    createApiKey.mutate(
      {
        name: name.trim(),
        permissions,
      },
      {
        onSuccess: (response) => {
          setCreatedKey(response.key)
        },
      }
    )
  }

  // 复制 key 到剪贴板
  const handleCopy = async () => {
    if (!createdKey) return
    try {
      await navigator.clipboard.writeText(createdKey)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('复制失败:', err)
    }
  }

  // 关闭对话框
  const handleClose = () => {
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <KeyRound className="h-5 w-5" />
            创建 API Key
          </DialogTitle>
          <DialogDescription>
            创建用于 API 访问认证的 API Key
          </DialogDescription>
        </DialogHeader>

        {createdKey ? (
          // 创建成功：显示明文 key
          <div className="space-y-4 py-2">
            <Alert className="border-amber-500/50 bg-amber-50 dark:bg-amber-950/20">
              <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
              <AlertDescription className="text-amber-700 dark:text-amber-300 text-sm">
                请立即复制并妥善保存此 API Key。出于安全考虑，关闭此对话框后将无法再次查看。
              </AlertDescription>
            </Alert>

            <div className="space-y-2">
              <Label className="text-xs">API Key（明文，仅此一次显示）</Label>
              <div className="flex items-center gap-2">
                <code className="flex-1 p-2.5 rounded border bg-muted font-mono text-xs break-all">
                  {createdKey}
                </code>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={handleCopy}
                  title="复制"
                  className="shrink-0"
                >
                  {copied ? (
                    <Check className="h-4 w-4 text-emerald-500" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>

            <DialogFooter>
              <Button onClick={handleClose} className="w-full">
                我已保存，关闭
              </Button>
            </DialogFooter>
          </div>
        ) : (
          // 创建表单
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="api-key-name">API Key 名称</Label>
              <Input
                id="api-key-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例如：生产环境、开发测试"
                autoFocus
              />
              <p className="text-xs text-muted-foreground">
                用于识别此 API Key 的用途
              </p>
            </div>

            <div className="space-y-2">
              <Label>权限</Label>
              <div className="flex gap-2">
                {AVAILABLE_PERMISSIONS.map((perm) => {
                  const isSelected = permissions.includes(perm)
                  return (
                    <button
                      key={perm}
                      type="button"
                      onClick={() => togglePermission(perm)}
                      className={`px-3 py-1.5 rounded-md border text-sm transition-colors ${
                        isSelected
                          ? 'bg-primary text-primary-foreground border-primary'
                          : 'bg-background text-muted-foreground border-input hover:bg-muted'
                      }`}
                    >
                      {perm}
                    </button>
                  )
                })}
              </div>
              <div className="flex flex-wrap gap-1 mt-1">
                {permissions.map((p) => (
                  <Badge key={p} variant="secondary" className="text-[10px]">
                    {p}
                  </Badge>
                ))}
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={handleClose}>
                取消
              </Button>
              <Button
                onClick={handleCreate}
                disabled={!name.trim() || createApiKey.isPending}
              >
                {createApiKey.isPending && (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                )}
                创建
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

'use client'

// API Key 列表组件
// 显示所有 API Key，支持撤销操作

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Trash2, KeyRound, Clock, Loader2 } from 'lucide-react'
import { useApiKeys, useRevokeApiKey } from '@/lib/hooks/use-api-keys'
import type { ApiKey } from '@/lib/api/api-keys'

// 格式化时间
function formatTime(time?: string | null): string {
  if (!time) return '从未使用'
  try {
    const date = new Date(time)
    return date.toLocaleString()
  } catch {
    return time
  }
}

interface ApiKeyListProps {
  onCreateClick?: () => void
}

export function ApiKeyList({ onCreateClick }: ApiKeyListProps) {
  const { data: apiKeys, isLoading } = useApiKeys()
  const revokeApiKey = useRevokeApiKey()

  // 撤销 API Key
  const handleRevoke = (key: ApiKey) => {
    if (window.confirm(`确定要撤销 API Key「${key.name}」吗？此操作无法撤销。`)) {
      revokeApiKey.mutate(key.id)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!apiKeys || apiKeys.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 text-center">
          <KeyRound className="h-10 w-10 text-muted-foreground/50 mb-3" />
          <p className="text-sm text-muted-foreground mb-3">
            暂无 API Key
          </p>
          {onCreateClick && (
            <Button variant="outline" size="sm" onClick={onCreateClick}>
              创建第一个 API Key
            </Button>
          )}
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-base">
          <span className="flex items-center gap-2">
            <KeyRound className="h-4 w-4" />
            API Keys（{apiKeys.length}）
          </span>
          {onCreateClick && (
            <Button variant="outline" size="sm" onClick={onCreateClick}>
              创建 API Key
            </Button>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {apiKeys.map((key) => (
          <div
            key={key.id}
            className="flex items-center justify-between gap-3 p-3 rounded border bg-muted/30"
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-medium text-sm truncate">{key.name}</span>
                <div className="flex gap-1">
                  {key.permissions.map((p) => (
                    <Badge
                      key={p}
                      variant="secondary"
                      className={`text-[10px] ${
                        p === 'write'
                          ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                          : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                      }`}
                    >
                      {p}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  最后使用：{formatTime(key.last_used_at)}
                </span>
                <span>·</span>
                <span>
                  创建于：{formatTime(key.created)}
                </span>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="text-destructive hover:text-destructive hover:bg-destructive/10 shrink-0"
              onClick={() => handleRevoke(key)}
              disabled={revokeApiKey.isPending}
              title="撤销"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

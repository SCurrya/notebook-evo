'use client'

// API Key 管理页面
// 管理用于 API 访问认证的 API Keys（区别于 AI 提供商凭证管理）
// 路径：/settings/api-access

import { useState } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { PageHeader } from '@/components/ui/page-header'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { KeyRound, Plus, ShieldAlert, Info } from 'lucide-react'
import { ApiKeyDialog } from '@/components/settings/ApiKeyDialog'
import { ApiKeyList } from '@/components/settings/ApiKeyList'

export default function ApiAccessPage() {
  const [dialogOpen, setDialogOpen] = useState(false)

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto animate-fade-in">
        <PageHeader
          title="API 访问密钥"
          description="管理用于 API 访问认证的 API Keys，支持通过 X-API-Key 头或 Authorization: ApiKey 认证"
          icon={KeyRound}
          actions={
            <Button size="sm" onClick={() => setDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              创建 API Key
            </Button>
          }
        />

        <div className="p-6 space-y-4 max-w-3xl">
          {/* 安全提示 */}
          <Alert>
            <ShieldAlert className="h-4 w-4" />
            <AlertTitle>安全说明</AlertTitle>
            <AlertDescription className="text-sm">
              <ul className="list-disc list-inside space-y-1 mt-1">
                <li>API Key 使用 SHA-256 哈希存储，明文仅在创建时返回一次</li>
                <li>请将 API Key 保存在安全的位置，关闭创建对话框后无法再次查看</li>
                <li>撤销 API Key 后立即失效，无法恢复</li>
                <li>建议为不同用途创建独立的 API Key，并仅授予所需的最小权限</li>
              </ul>
            </AlertDescription>
          </Alert>

          {/* 使用说明 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Info className="h-4 w-4" />
                使用方式
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div>
                <p className="font-medium mb-1">方式一：X-API-Key 请求头</p>
                <pre className="bg-muted p-2 rounded text-xs overflow-x-auto">
{`X-API-Key: on_xxxxxxxxxxxxxxxxxxxxxxxx`}
                </pre>
              </div>
              <div>
                <p className="font-medium mb-1">方式二：Authorization 头</p>
                <pre className="bg-muted p-2 rounded text-xs overflow-x-auto">
{`Authorization: ApiKey on_xxxxxxxxxxxxxxxxxxxxxxxx`}
                </pre>
              </div>
              <p className="text-xs text-muted-foreground">
                注意：API Key 认证为可选认证方式。仅当请求携带 API Key 时才进行校验，否则使用其他认证机制。
              </p>
            </CardContent>
          </Card>

          {/* API Key 列表 */}
          <ApiKeyList onCreateClick={() => setDialogOpen(true)} />
        </div>
      </div>

      {/* 创建 API Key 对话框 */}
      <ApiKeyDialog open={dialogOpen} onOpenChange={setDialogOpen} />
    </AppShell>
  )
}

'use client'

// 系统健康状态页面
// 一屏展示整个应用栈的健康情况：数据库、模型、worker、版本等

import {
  Activity,
  CheckCircle2,
  Cpu,
  Database,
  RefreshCw,
  Server,
  Sparkles,
  XCircle,
} from 'lucide-react'

import { AppShell } from '@/components/layout/AppShell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader } from '@/components/ui/page-header'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { useSystemStatus } from '@/lib/hooks/use-system'

function formatUptime(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  if (hours > 0) return `${hours}小时 ${minutes}分`
  if (minutes > 0) return `${minutes}分 ${secs}秒`
  return `${secs}秒`
}

function StatusBadge({ ok, okLabel, failLabel }: { ok: boolean; okLabel: string; failLabel: string }) {
  return ok ? (
    <Badge className="bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300">
      <CheckCircle2 className="mr-1 h-3 w-3" />
      {okLabel}
    </Badge>
  ) : (
    <Badge className="bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300">
      <XCircle className="mr-1 h-3 w-3" />
      {failLabel}
    </Badge>
  )
}

function ProviderCell({ provider, count }: { provider: string; count: number }) {
  return (
    <div className="flex items-center justify-between rounded-lg border px-3 py-2">
      <span className="font-mono text-xs">{provider}</span>
      <Badge variant="secondary">{count} 个模型</Badge>
    </div>
  )
}

export default function SystemPage() {
  const { data, isLoading, isError, refetch, isFetching } = useSystemStatus()

  return (
    <AppShell>
      <PageHeader
        title="系统健康状态"
        description="数据库、模型与后台服务的一屏总览。"
        icon={Activity}
      />

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {isLoading ? (
          <div className="flex items-center justify-center min-h-[300px]">
            <LoadingSpinner size="lg" />
          </div>
        ) : isError || !data ? (
          <Card>
            <CardContent className="py-8 text-center">
              <p className="text-sm text-muted-foreground">
                无法获取系统状态。请确认 API 服务正在运行。
              </p>
            </CardContent>
          </Card>
        ) : (
          <>
            {/* 总体状态 */}
            <Card className={data.ok ? 'border-green-200 dark:border-green-800' : 'border-red-200 dark:border-red-800'}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Server className="h-5 w-5" />
                  总体状态
                </CardTitle>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => refetch()}
                  disabled={isFetching}
                >
                  <RefreshCw className={`mr-1 h-3 w-3 ${isFetching ? 'animate-spin' : ''}`} />
                  刷新
                </Button>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-3">
                  <StatusBadge
                    ok={data.ok}
                    okLabel="全部服务正常"
                    failLabel="存在异常，请检查下方项目"
                  />
                  <span className="text-xs text-muted-foreground">
                    运行时间 {formatUptime(data.uptime_seconds)} · v{data.version}
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* 基础设施 */}
            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Database className="h-4 w-4" />
                    数据库
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">SurrealDB 连接</span>
                    <StatusBadge ok={data.db.connected} okLabel="已连接" failLabel="连接失败" />
                  </div>
                  {data.db_stats && Object.keys(data.db_stats).some((k) => k !== 'error') && (
                    <div className="mt-3 grid grid-cols-3 gap-2">
                      <div className="rounded-md bg-muted/50 px-2 py-1.5 text-center">
                        <div className="text-sm font-semibold">{data.db_stats.notebook ?? 0}</div>
                        <div className="text-[10px] text-muted-foreground">笔记本</div>
                      </div>
                      <div className="rounded-md bg-muted/50 px-2 py-1.5 text-center">
                        <div className="text-sm font-semibold">{data.db_stats.source ?? 0}</div>
                        <div className="text-[10px] text-muted-foreground">来源</div>
                      </div>
                      <div className="rounded-md bg-muted/50 px-2 py-1.5 text-center">
                        <div className="text-sm font-semibold">{data.db_stats.note ?? 0}</div>
                        <div className="text-[10px] text-muted-foreground">笔记</div>
                      </div>
                    </div>
                  )}
                  {data.db.error && (
                    <p className="mt-2 text-xs text-red-600 dark:text-red-400 break-all">{data.db.error}</p>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Sparkles className="h-4 w-4" />
                    模型
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">已注册模型</span>
                    <Badge variant="secondary">{data.models.count} 个</Badge>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* 模型按 Provider 分布 */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Cpu className="h-4 w-4" />
                  模型 Provider 分布
                </CardTitle>
                <CardDescription className="text-xs">
                  各提供商下注册的模型数量
                </CardDescription>
              </CardHeader>
              <CardContent>
                {data.models.by_provider && Object.keys(data.models.by_provider).length > 0 ? (
                  <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                    {Object.entries(data.models.by_provider).map(([provider, count]) => (
                      <ProviderCell key={provider} provider={provider} count={count} />
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">暂无模型配置</p>
                )}
                {data.models.error && (
                  <p className="mt-2 text-xs text-red-600 dark:text-red-400 break-all">{data.models.error}</p>
                )}
              </CardContent>
            </Card>

            {/* 后台 Worker */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Activity className="h-4 w-4" />
                  后台 Worker
                </CardTitle>
                <CardDescription className="text-xs">
                  负责异步处理来源上传、嵌入生成等任务
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">命令队列 Worker</span>
                  <StatusBadge ok={data.worker.running} okLabel="运行中" failLabel="未运行" />
                </div>
                {!data.worker.running && (
                  <p className="mt-2 text-xs text-amber-600 dark:text-amber-400">
                    异步处理不可用。请使用 run_api.py 启动（内置 worker），或设置
                    OPEN_NOTEBOOK_WORKER_MAX_TASKS 环境变量。
                  </p>
                )}
              </CardContent>
            </Card>

            {/* 运行环境 */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Server className="h-4 w-4" />
                  运行环境
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-2 text-xs sm:grid-cols-2">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">API 版本</span>
                    <span className="font-mono">{data.version}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Python</span>
                    <span className="font-mono">{data.python}</span>
                  </div>
                  <div className="flex justify-between sm:col-span-2">
                    <span className="text-muted-foreground">系统</span>
                    <span className="font-mono">{data.platform}</span>
                  </div>
                  <div className="flex justify-between sm:col-span-2">
                    <span className="text-muted-foreground">检查时间</span>
                    <span className="font-mono">{new Date(data.timestamp).toLocaleString('zh-CN')}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </AppShell>
  )
}

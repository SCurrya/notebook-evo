'use client'

// 共享笔记本访问页面
// 通过 query string 中的 token 参数访问共享笔记本
// 使用 query param 而非 dynamic route 以支持静态导出（Capacitor 移动端）

import { Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { SharedNotebookView } from '@/components/share/SharedNotebookView'
import { PageHeader } from '@/components/ui/page-header'
import { BookOpen } from 'lucide-react'

function SharedNotebookContent() {
  const searchParams = useSearchParams()
  const rawToken = searchParams?.get('token') || ''
  const token = rawToken ? decodeURIComponent(rawToken) : ''

  return (
    <div className="flex-1 overflow-y-auto animate-fade-in">
      {token ? (
        <SharedNotebookView token={token} />
      ) : (
        <div className="flex items-center justify-center min-h-[400px]">
          <p className="text-sm text-muted-foreground">无效的共享链接</p>
        </div>
      )}
    </div>
  )
}

export default function SharedNotebookPage() {
  return (
    <AppShell>
      <PageHeader
        title="共享笔记本"
        description="通过共享链接查看他人公开的笔记本内容。"
        icon={BookOpen}
      />
      <Suspense fallback={
        <div className="flex-1 flex items-center justify-center">
          <p className="text-sm text-muted-foreground">加载中...</p>
        </div>
      }>
        <SharedNotebookContent />
      </Suspense>
    </AppShell>
  )
}

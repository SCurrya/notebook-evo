'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import {
  BookOpen, FileText, StickyNote, Sparkles, Network, ListTodo, ChevronRight,
  Search, Share2, BarChart3, Settings2,
} from 'lucide-react'
import { analyticsApi, AnalyticsSummary } from '@/lib/api/analytics'
import { useTranslation } from '@/lib/hooks/use-translation'

function StatCard({
  label, value, icon: Icon, href, color,
}: {
  label: string
  value: number | string
  icon: React.ElementType
  href: string
  color: string
}) {
  return (
    <Link
      href={href}
      className="group rounded-xl border bg-card p-4 transition-shadow hover:shadow-md"
    >
      <div className="flex items-center justify-between">
        <div className={`rounded-lg p-2 ${color}`}>
          <Icon className="h-5 w-5" />
        </div>
        <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
      </div>
      <div className="mt-3 text-2xl font-bold">{value}</div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </Link>
  )
}

export default function DashboardPage() {
  const { t } = useTranslation()
  const [data, setData] = useState<AnalyticsSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    analyticsApi.summary()
      .then((summary) => {
        if (!cancelled) {
          setData(summary)
          setError(null)
        }
      })
      .catch(() => {
        if (!cancelled) setError('failed')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const counts = data?.counts ?? {
    notebook: 0, source: 0, note: 0, insight: 0, task: 0, entity: 0, relation: 0,
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t('common.dashboard') || '总览'}</h1>
        <p className="text-sm text-muted-foreground">
          {t('common.welcome') || '欢迎回来，你的知识库一览。'}
        </p>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        <StatCard label={t('notebooks.title') || '笔记本'} value={counts.notebook} icon={BookOpen} href="/notebooks" color="bg-blue-500/10 text-blue-600 dark:text-blue-400" />
        <StatCard label={t('sources.title') || '来源'} value={counts.source} icon={FileText} href="/sources" color="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" />
        <StatCard label={t('notes.title') || '笔记'} value={counts.note} icon={StickyNote} href="/notebooks" color="bg-amber-500/10 text-amber-600 dark:text-amber-400" />
        <StatCard label={t('common.insights') || '洞察'} value={counts.insight} icon={Sparkles} href="/notebooks" color="bg-purple-500/10 text-purple-600 dark:text-purple-400" />
        <StatCard label={t('common.knowledgeGraph') || '知识图谱'} value={`${counts.entity} / ${counts.relation}`} icon={Network} href="/knowledge-graph" color="bg-cyan-500/10 text-cyan-600 dark:text-cyan-400" />
        <StatCard label={t('agents.title') || 'Agent 任务'} value={counts.task} icon={ListTodo} href="/agents" color="bg-rose-500/10 text-rose-600 dark:text-rose-400" />
        <StatCard label={t('common.search') || '语义搜索'} value={counts.source} icon={Search} href="/search" color="bg-indigo-500/10 text-indigo-600 dark:text-indigo-400" />
        <StatCard label={t('common.eval') || 'RAG 评估'} value={counts.note} icon={BarChart3} href="/eval" color="bg-teal-500/10 text-teal-600 dark:text-teal-400" />
      </div>

      {/* 近期笔记本 */}
      <div className="rounded-xl border bg-card p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold">{t('common.recent') || '近期笔记本'}</h2>
          <Link href="/notebooks" className="text-xs text-primary hover:underline">
            {t('common.viewAll') || '查看全部'}
          </Link>
        </div>
        {loading ? (
          <p className="py-6 text-center text-sm text-muted-foreground">加载中...</p>
        ) : error ? (
          <p className="py-6 text-center text-sm text-red-500">加载失败</p>
        ) : data?.recent_notebooks.length ? (
          <div className="space-y-1">
            {data.recent_notebooks.map((nb) => (
              <Link
                key={nb.id}
                href={`/notebooks/${nb.id}`}
                className="flex items-center justify-between rounded-lg px-2 py-2 hover:bg-muted/50"
              >
                <div className="flex items-center gap-3">
                  <BookOpen className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">{nb.name}</span>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </Link>
            ))}
          </div>
        ) : (
          <div className="py-6 text-center">
            <p className="text-sm text-muted-foreground">{t('common.noNotebooks') || '还没有笔记本'}</p>
            <Link href="/notebooks" className="mt-2 inline-block text-sm text-primary hover:underline">
              {t('notebooks.newNotebook') || '创建笔记本'}
            </Link>
          </div>
        )}
      </div>

      {/* 快捷入口 */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Link href="/knowledge-graph" className="rounded-xl border bg-card p-3 text-center text-xs text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground">
          <Network className="mx-auto mb-1 h-4 w-4" /> 知识图谱
        </Link>
        <Link href="/share" className="rounded-xl border bg-card p-3 text-center text-xs text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground">
          <Share2 className="mx-auto mb-1 h-4 w-4" /> 分享管理
        </Link>
        <Link href="/studio" className="rounded-xl border bg-card p-3 text-center text-xs text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground">
          <Sparkles className="mx-auto mb-1 h-4 w-4" /> Studio 创作
        </Link>
        <Link href="/settings" className="rounded-xl border bg-card p-3 text-center text-xs text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground">
          <Settings2 className="mx-auto mb-1 h-4 w-4" /> 设置
        </Link>
      </div>
    </div>
  )
}

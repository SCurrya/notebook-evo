'use client'

// Studio 主页面
// 提供 Studio 模块导航，展示四个功能模块入口

import Link from 'next/link'
import { PageHeader } from '@/components/ui/page-header'
import { AppShell } from '@/components/layout/AppShell'
import { Card } from '@/components/ui/card'
import { FileText, FileBarChart, HelpCircle, Clock } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { StudioLayout } from '@/components/studio/StudioLayout'

export default function StudioPage() {
  const { t } = useTranslation()

  const modules = [
    {
      title: t('studio.templates'),
      description: t('studio.templatesDesc'),
      href: '/studio/templates',
      icon: FileText,
    },
    {
      title: t('studio.report'),
      description: t('studio.reportDesc'),
      href: '/studio/report',
      icon: FileBarChart,
    },
    {
      title: t('studio.faq'),
      description: t('studio.faqDesc'),
      href: '/studio/faq',
      icon: HelpCircle,
    },
    {
      title: t('studio.timeline'),
      description: t('studio.timelineDesc'),
      href: '/studio/timeline',
      icon: Clock,
    },
  ]

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto animate-fade-in">
        <PageHeader
          title={t('studio.title')}
          description={t('studio.desc')}
          icon={FileBarChart}
        />

        <div className="page-container py-6">
          <StudioLayout>
            <div className="mb-8 grid gap-6 lg:grid-cols-[1.2fr_0.8fr] lg:items-end">
              <div className="max-w-2xl space-y-4">
                <div className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-background/70 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                  <span className="size-2 rounded-full bg-primary" />
                  Research Studio
                </div>
                <div className="space-y-3">
                  <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                    {t('studio.desc')}
                  </h2>
                  <p className="max-w-2xl text-sm leading-7 text-muted-foreground sm:text-base">
                    这里把报告、FAQ、时间线和模板管理收进同一套研究工作台，偏安静、偏笔记感，适合长时间处理内容。
                  </p>
                </div>
              </div>
              <Card className="rounded-[28px] border-border/70 bg-background/70 p-4 shadow-none">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="rounded-2xl border border-border/70 bg-card/80 p-3">
                    <div className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Modules</div>
                    <div className="mt-1 text-lg font-semibold">4</div>
                  </div>
                  <div className="rounded-2xl border border-border/70 bg-card/80 p-3">
                    <div className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Style</div>
                    <div className="mt-1 text-lg font-semibold">NotebookLM</div>
                  </div>
                </div>
              </Card>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:gap-5">
              {modules.map((module, index) => (
                <Link key={module.href} href={module.href} className="group">
                  <Card className="group relative h-full overflow-hidden rounded-[28px] border-border/70 bg-background/80 p-6 transition-all duration-300 hover:-translate-y-1 hover:border-primary/25 hover:shadow-[0_24px_50px_-32px_color-mix(in_oklch,var(--primary)_32%,transparent)]">
                    <div className="absolute inset-0 bg-[linear-gradient(135deg,transparent_0%,transparent_55%,color-mix(in_oklch,var(--primary)_6%,transparent)_100%)] opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
                    <div className="relative flex items-start gap-4">
                      <div className="flex size-12 shrink-0 items-center justify-center rounded-2xl border border-border/70 bg-card text-primary shadow-[0_10px_30px_-18px_color-mix(in_oklch,var(--primary)_40%,transparent)]">
                        <module.icon className="size-6" />
                      </div>
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                            0{index + 1}
                          </span>
                          <h3 className="text-lg font-semibold">{module.title}</h3>
                        </div>
                        <p className="max-w-md text-sm leading-6 text-muted-foreground">
                          {module.description}
                        </p>
                      </div>
                    </div>
                  </Card>
                </Link>
              ))}
            </div>
          </StudioLayout>
        </div>
      </div>
    </AppShell>
  )
}

'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

interface PageHeaderProps extends React.ComponentProps<'div'> {
  title: string
  description?: string
  icon?: React.ComponentType<{ className?: string }>
  actions?: React.ReactNode
  stats?: React.ReactNode
}

function PageHeader({
  title,
  description,
  icon: Icon,
  actions,
  stats,
  className,
  ...props
}: PageHeaderProps) {
  return (
    <div className={cn('relative border-b border-border/60 bg-background/72 backdrop-blur-sm', className)} {...props}>
      <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_top_left,_color-mix(in_oklch,var(--primary)_8%,transparent),_transparent_32%)]" />
      <div className="relative page-container py-5 sm:py-6 lg:py-7">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex items-start gap-4">
            {Icon && (
              <div className="flex size-11 shrink-0 items-center justify-center rounded-2xl border border-border/70 bg-card text-primary elevation-1">
                <Icon className="size-5" />
              </div>
            )}
            <div className="space-y-1 max-w-3xl">
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                Open Notebook
              </p>
              <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl lg:text-[2rem]">
                {title}
              </h1>
              {description && (
                <p className="max-w-2xl text-sm leading-6 text-muted-foreground sm:text-base">
                  {description}
                </p>
              )}
            </div>
          </div>
          {actions && (
            <div className="flex flex-wrap items-center gap-2 lg:justify-end">
              {actions}
            </div>
          )}
        </div>
        {stats && (
          <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
            {stats}
          </div>
        )}
      </div>
    </div>
  )
}

interface StatCardProps {
  label: string
  value: string | number
  icon?: React.ComponentType<{ className?: string }>
  trend?: string
  trendType?: 'up' | 'down' | 'neutral'
}

function StatCard({ label, value, icon: Icon, trend, trendType = 'neutral' }: StatCardProps) {
  const trendColor = {
    up: 'text-success',
    down: 'text-destructive',
    neutral: 'text-muted-foreground',
  }[trendType]

  return (
    <div className="rounded-2xl border border-border/70 bg-card/80 p-3.5 shadow-sm transition-all duration-normal ease-standard hover:-translate-y-0.5 hover:shadow-md">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-muted-foreground sm:text-sm">{label}</span>
        {Icon && <Icon className="size-4 text-muted-foreground/60" />}
      </div>
      <div className="mt-1.5 flex items-baseline gap-2">
        <span className="text-xl font-semibold sm:text-2xl">{value}</span>
        {trend && <span className={cn('text-xs font-medium', trendColor)}>{trend}</span>}
      </div>
    </div>
  )
}

export { PageHeader, StatCard }

'use client'

import * as React from "react"
import { cn } from "@/lib/utils"

/**
 * 页面头部组件 - 统一的页面标题区域
 * 包含标题、描述、操作按钮和可选的统计信息
 */
interface PageHeaderProps extends React.ComponentProps<"div"> {
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
    <div
      className={cn(
        "relative overflow-hidden border-b border-border/50",
        className
      )}
      {...props}
    >
      {/* 装饰性渐变背景 */}
      <div className="absolute inset-0 gradient-hero pointer-events-none" />

      <div className="relative page-container py-6 sm:py-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3 sm:gap-4">
            {Icon && (
              <div className="flex size-11 sm:size-12 shrink-0 items-center justify-center rounded-xl gradient-primary text-primary-foreground elevation-2">
                <Icon className="size-5 sm:size-6" />
              </div>
            )}
            <div className="space-y-1">
              <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
                {title}
              </h1>
              {description && (
                <p className="text-sm text-muted-foreground sm:text-base text-pretty">
                  {description}
                </p>
              )}
            </div>
          </div>
          {actions && (
            <div className="flex items-center gap-2 shrink-0">
              {actions}
            </div>
          )}
        </div>
        {stats && (
          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
            {stats}
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * 统计卡片 - 用于 PageHeader 的 stats 区域
 */
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
    <div className="rounded-xl border bg-card/50 p-3 sm:p-4 backdrop-blur-sm transition-all duration-normal ease-standard hover:elevation-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-muted-foreground sm:text-sm">
          {label}
        </span>
        {Icon && (
          <Icon className="size-4 text-muted-foreground/60" />
        )}
      </div>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="text-xl font-bold sm:text-2xl">{value}</span>
        {trend && (
          <span className={cn("text-xs font-medium", trendColor)}>
            {trend}
          </span>
        )}
      </div>
    </div>
  )
}

export { PageHeader, StatCard }

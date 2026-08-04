'use client'

import * as React from 'react'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface StudioLayoutProps {
  children: React.ReactNode
  className?: string
}

export function StudioLayout({ children, className }: StudioLayoutProps) {
  return (
    <div className={cn('space-y-6', className)}>
      <Card className="research-panel relative overflow-hidden rounded-[32px] border-border/70 bg-[linear-gradient(180deg,color-mix(in_oklch,var(--card)_96%,white)_0%,color-mix(in_oklch,var(--background)_92%,white)_100%)] p-6 shadow-[0_30px_80px_-55px_color-mix(in_oklch,var(--primary)_24%,transparent)] sm:p-8">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,_color-mix(in_oklch,var(--primary)_10%,transparent),_transparent_34%)]" />
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-border to-transparent" />
        <div className="pointer-events-none absolute left-0 top-0 h-full w-px bg-gradient-to-b from-transparent via-border/80 to-transparent" />
        <div className="pointer-events-none absolute inset-x-6 top-6 h-1 rounded-full bg-gradient-to-r from-transparent via-primary/15 to-transparent" />
        <div className="relative">{children}</div>
      </Card>
    </div>
  )
}

'use client'

// 时间线组件
// 使用垂直时间线布局展示事件，按时间顺序排列

import { Clock, Calendar } from 'lucide-react'
import type { TimelineEvent } from '@/lib/api/studio'
import { useTranslation } from '@/lib/hooks/use-translation'

interface TimelineProps {
  events: TimelineEvent[]
}

export function Timeline({ events }: TimelineProps) {
  const { t } = useTranslation()

  if (events.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <Clock className="h-12 w-12 mx-auto mb-3 opacity-50" />
        <p>{t('studio.noTimelineEvents')}</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-4">
        <Clock className="h-5 w-5 text-primary" />
        <h3 className="text-lg font-semibold">{t('studio.timelineResult')}</h3>
        <span className="text-sm text-muted-foreground">({events.length})</span>
      </div>

      {/* 垂直时间线 */}
      <div className="relative pl-8">
        {/* 时间线竖线 */}
        <div className="absolute left-3 top-2 bottom-2 w-0.5 bg-border" />

        <div className="space-y-6">
          {events.map((event, index) => (
            <div key={index} className="relative">
              {/* 时间线节点 */}
              <div className="absolute -left-6 top-1 flex h-5 w-5 items-center justify-center rounded-full border-2 border-primary bg-background">
                <div className="h-2 w-2 rounded-full bg-primary" />
              </div>

              {/* 事件内容 */}
              <div className="rounded-lg border bg-background p-4">
                <div className="flex items-center gap-2 mb-1">
                  <Calendar className="h-4 w-4 text-primary" />
                  <span className="text-sm font-semibold text-primary">
                    {event.date}
                  </span>
                </div>
                <p className="text-sm text-foreground">{event.event}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

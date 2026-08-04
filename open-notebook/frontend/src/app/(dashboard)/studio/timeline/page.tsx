'use client'

// Studio 时间线生成页面
// 选择笔记本，从内容中提取事件并按时间排序生成时间线

import { useState } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { PageHeader } from '@/components/ui/page-header'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Timeline } from '@/components/studio/Timeline'
import { StudioLayout } from '@/components/studio/StudioLayout'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { useGenerateTimeline } from '@/lib/hooks/use-studio'
import type { TimelineEvent } from '@/lib/api/studio'
import { Clock, Loader2 } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'

export default function StudioTimelinePage() {
  const { t } = useTranslation()
  const { data: notebooks, isLoading: notebooksLoading } = useNotebooks()
  const generateTimeline = useGenerateTimeline()

  const [notebookId, setNotebookId] = useState('')
  const [events, setEvents] = useState<TimelineEvent[]>([])

  const handleGenerate = async () => {
    if (!notebookId) return
    setEvents([])
    const result = await generateTimeline.mutateAsync({
      notebook_id: notebookId,
    })
    setEvents(result.events)
  }

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto animate-fade-in">
        <PageHeader
          title={t('studio.timeline')}
          description={t('studio.timelineDesc')}
          icon={Clock}
        />

        <div className="page-container py-6 space-y-6">
          <StudioLayout>
            <div className="grid gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
              <Card className="rounded-[24px] border-border/70 bg-background/80 p-6 shadow-none">
                <div className="space-y-5">
                  <div className="space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                      生成参数
                    </p>
                    <h2 className="text-xl font-semibold">{t('studio.generateTimeline')}</h2>
                  </div>

                  <div className="space-y-2">
                    <Label>{t('studio.selectNotebook')}</Label>
                    <Select value={notebookId} onValueChange={setNotebookId}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder={t('studio.selectNotebookPlaceholder')} />
                      </SelectTrigger>
                      <SelectContent>
                        {notebooksLoading ? (
                          <SelectItem value="_loading" disabled>
                            {t('common.loading')}
                          </SelectItem>
                        ) : (
                          notebooks?.map((nb) => (
                            <SelectItem key={nb.id} value={nb.id}>
                              {nb.name}
                            </SelectItem>
                          ))
                        )}
                      </SelectContent>
                    </Select>
                  </div>

                  <Button
                    onClick={handleGenerate}
                    disabled={!notebookId || generateTimeline.isPending}
                    className="w-full"
                  >
                    {generateTimeline.isPending ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        {t('studio.generating')}
                      </>
                    ) : (
                      t('studio.generateTimeline')
                    )}
                  </Button>
                </div>
              </Card>

              <div className="min-w-0">
                {events.length > 0 ? (
                  <Timeline events={events} />
                ) : (
                  <Card className="rounded-[24px] border-border/70 bg-background/80 p-10 text-center text-sm text-muted-foreground shadow-none">
                    生成完成后，事件时间线会在这里显示。
                  </Card>
                )}
              </div>
            </div>
          </StudioLayout>
        </div>
      </div>
    </AppShell>
  )
}

'use client'

import { AppShell } from '@/components/layout/AppShell'
import { RebuildEmbeddings } from './components/RebuildEmbeddings'
import { SystemInfo } from './components/SystemInfo'
import { useTranslation } from '@/lib/hooks/use-translation'
import { PageHeader } from '@/components/ui/page-header'
import { Wrench } from 'lucide-react'

export default function AdvancedPage() {
  const { t } = useTranslation()
  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <PageHeader
          title={t('advanced.title')}
          description={t('advanced.desc')}
          icon={Wrench}
        />

        <div className="page-container py-6">
          <div className="max-w-4xl mx-auto space-y-6">
            <SystemInfo />
            <RebuildEmbeddings />
          </div>
        </div>
      </div>
    </AppShell>
  )
}

'use client'

import { AppShell } from '@/components/layout/AppShell'
import { SettingsForm } from './components/SettingsForm'
import { useSettings } from '@/lib/hooks/use-settings'
import { Button } from '@/components/ui/button'
import { RefreshCw, Settings } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { PageHeader } from '@/components/ui/page-header'

export default function SettingsPage() {
  const { t } = useTranslation()
  const { refetch } = useSettings()

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto animate-fade-in">
        <PageHeader
          title={t('navigation.settings')}
          description="配置 API 密钥、模型参数和应用偏好"
          icon={Settings}
          actions={
            <Button
              variant="outline"
              size="icon"
              onClick={() => refetch()}
              aria-label="刷新"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          }
        />

        <div className="page-container py-6">
          <div className="max-w-4xl animate-slide-up">
            <SettingsForm />
          </div>
        </div>
      </div>
    </AppShell>
  )
}

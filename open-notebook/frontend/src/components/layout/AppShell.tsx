'use client'

import { Menu, X } from 'lucide-react'
import Image from 'next/image'

import { AppSidebar } from './AppSidebar'
import { SetupBanner } from './SetupBanner'
import { Button } from '@/components/ui/button'
import { useSidebarStore } from '@/lib/stores/sidebar-store'
import { useTranslation } from '@/lib/hooks/use-translation'

interface AppShellProps {
  children: React.ReactNode
}

export function AppShell({ children }: AppShellProps) {
  const { t } = useTranslation()
  const { isMobileOpen, setMobileOpen } = useSidebarStore()

  return (
    <div className="flex h-screen overflow-hidden p-0 sm:p-2 lg:p-4">
      {/* 移动端顶部栏 */}
      <div className="md:hidden flex h-12 shrink-0 items-center gap-3 border-b border-sidebar-border/60 px-3">
        <Button
          variant="ghost"
          size="icon"
          className="size-8 shrink-0"
          onClick={() => setMobileOpen(!isMobileOpen)}
          aria-label={isMobileOpen ? t('common.close') : t('common.menu')}
          title={isMobileOpen ? t('common.close') : t('common.menu')}
        >
          {isMobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </Button>
        <div className="flex min-w-0 items-center gap-2">
          <div className="size-7 shrink-0 rounded-lg gradient-primary flex items-center justify-center">
            <Image src="/logo.svg" alt={t('common.appName')} width={16} height={16} />
          </div>
          <span className="truncate text-sm font-semibold text-foreground tracking-tight">
            {t('common.appName')}
          </span>
        </div>
      </div>

      <div className="app-shell-surface flex w-full overflow-hidden rounded-none sm:rounded-[28px]">
        <AppSidebar />
        <main className="flex min-h-0 flex-1 flex-col overflow-hidden bg-background/70">
          <SetupBanner />
          {children}
        </main>
      </div>
    </div>
  )
}

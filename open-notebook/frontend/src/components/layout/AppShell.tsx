'use client'

import { AppSidebar } from './AppSidebar'
import { SetupBanner } from './SetupBanner'

interface AppShellProps {
  children: React.ReactNode
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex h-screen overflow-hidden p-2 sm:p-3 lg:p-4">
      <div className="app-shell-surface flex w-full overflow-hidden rounded-[28px]">
        <AppSidebar />
        <main className="flex min-h-0 flex-1 flex-col overflow-hidden bg-background/70">
          <SetupBanner />
          {children}
        </main>
      </div>
    </div>
  )
}

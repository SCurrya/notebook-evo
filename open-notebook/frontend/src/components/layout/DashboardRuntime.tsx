'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ErrorBoundary } from '@/components/common/ErrorBoundary'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { CommandPalette } from '@/components/common/CommandPalette'
import { ModalProvider } from '@/components/providers/ModalProvider'
import { useAuth } from '@/lib/hooks/use-auth'
import { CreateDialogsProvider } from '@/lib/hooks/use-create-dialogs'
import { useVersionCheck } from '@/lib/hooks/use-version-check'

interface DashboardRuntimeProps {
  children: React.ReactNode
}

const LOCAL_DESKTOP_HOSTS = new Set(['127.0.0.1', 'localhost', '::1'])

function isDesktopHost() {
  return (
    typeof window !== 'undefined' &&
    LOCAL_DESKTOP_HOSTS.has(window.location.hostname) &&
    window.location.port === '8502'
  )
}

function DashboardChrome({ children }: DashboardRuntimeProps) {
  return (
    <ErrorBoundary>
      <CreateDialogsProvider>
        {children}
        <ModalProvider />
        <CommandPalette />
      </CreateDialogsProvider>
    </ErrorBoundary>
  )
}

export function DashboardRuntime({ children }: DashboardRuntimeProps) {
  const { isAuthenticated, isLoading } = useAuth()
  const router = useRouter()
  const [hasCheckedAuth, setHasCheckedAuth] = useState(false)
  const desktopHost = isDesktopHost()

  useVersionCheck()

  useEffect(() => {
    if (desktopHost) {
      setHasCheckedAuth(true)
      return
    }

    if (isLoading) return

    setHasCheckedAuth(true)

    if (!isAuthenticated) {
      const currentPath = window.location.pathname + window.location.search
      sessionStorage.setItem('redirectAfterLogin', currentPath)
      router.push('/login')
    }
  }, [desktopHost, isAuthenticated, isLoading, router])

  if (isLoading || !hasCheckedAuth) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner />
      </div>
    )
  }

  if (!desktopHost && !isAuthenticated) {
    return null
  }

  return <DashboardChrome>{children}</DashboardChrome>
}

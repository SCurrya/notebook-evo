'use client'

import { useCallback, useEffect, useState } from 'react'

/**
 * PWA beforeinstallprompt 事件类型。
 * 浏览器在满足安装条件时触发，但尚未标准化，因此需要自定义类型声明。
 */
interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[]
  readonly userChoice: Promise<{
    outcome: 'accepted' | 'dismissed'
    platform: string
  }>
  prompt: () => Promise<void>
}

/**
 * PWA Hook。
 *
 * 提供以下能力：
 * - 安装状态检测与触发安装提示
 * - 离线/在线状态监听
 * - Service Worker 更新检测
 *
 * 使用方式：
 *   const { canInstall, isInstalled, isOffline, hasUpdate, promptInstall } = usePWA()
 */
export function usePWA() {
  const [canInstall, setCanInstall] = useState(false)
  const [isInstalled, setIsInstalled] = useState(false)
  const [isOffline, setIsOffline] = useState(false)
  const [hasUpdate, setHasUpdate] = useState(false)
  const [deferredPrompt, setDeferredPrompt] =
    useState<BeforeInstallPromptEvent | null>(null)

  // 检测是否已安装（独立显示模式）
  useEffect(() => {
    if (typeof window === 'undefined') return

    const checkInstalled = () => {
      const standalone =
        window.matchMedia('(display-mode: standalone)').matches ||
        // iOS Safari 独立模式
        (window.navigator as unknown as { standalone?: boolean }).standalone ===
          true
      setIsInstalled(standalone)
    }

    checkInstalled()
    const mediaQuery = window.matchMedia('(display-mode: standalone)')
    mediaQuery.addEventListener('change', checkInstalled)
    return () => mediaQuery.removeEventListener('change', checkInstalled)
  }, [])

  // 监听 beforeinstallprompt 事件
  useEffect(() => {
    if (typeof window === 'undefined') return

    const handleBeforeInstallPrompt = (e: Event) => {
      // 阻止浏览器默认安装提示，由自定义组件接管
      e.preventDefault()
      setDeferredPrompt(e as BeforeInstallPromptEvent)
      setCanInstall(true)
    }

    const handleAppInstalled = () => {
      setCanInstall(false)
      setDeferredPrompt(null)
      setIsInstalled(true)
    }

    window.addEventListener(
      'beforeinstallprompt',
      handleBeforeInstallPrompt as EventListener
    )
    window.addEventListener('appinstalled', handleAppInstalled)

    return () => {
      window.removeEventListener(
        'beforeinstallprompt',
        handleBeforeInstallPrompt as EventListener
      )
      window.removeEventListener('appinstalled', handleAppInstalled)
    }
  }, [])

  // 监听在线/离线状态
  useEffect(() => {
    if (typeof window === 'undefined') return

    const handleOnline = () => setIsOffline(false)
    const handleOffline = () => setIsOffline(true)

    setIsOffline(!window.navigator.onLine)
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  // 监听 Service Worker 更新
  useEffect(() => {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) return

    const handleControllerChange = () => {
      setHasUpdate(true)
    }

    navigator.serviceWorker.addEventListener(
      'controllerchange',
      handleControllerChange
    )
    return () => {
      navigator.serviceWorker.removeEventListener(
        'controllerchange',
        handleControllerChange
      )
    }
  }, [])

  /**
   * 触发安装提示。
   * 仅在 canInstall 为 true 时有效，调用后清除延迟提示。
   * 返回用户是否接受安装。
   */
  const promptInstall = useCallback(async (): Promise<boolean> => {
    if (!deferredPrompt) return false

    await deferredPrompt.prompt()
    const choice = await deferredPrompt.userChoice
    setDeferredPrompt(null)
    setCanInstall(false)

    return choice.outcome === 'accepted'
  }, [deferredPrompt])

  /**
   * 应用 Service Worker 更新并重载页面。
   */
  const applyUpdate = useCallback(() => {
    if (typeof window === 'undefined') return
    window.location.reload()
  }, [])

  return {
    canInstall,
    isInstalled,
    isOffline,
    hasUpdate,
    promptInstall,
    applyUpdate,
  }
}

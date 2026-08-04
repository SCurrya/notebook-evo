'use client'

import { useEffect, useState } from 'react'
import { usePWA } from '@/lib/hooks/use-pwa'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Download, X, Smartphone } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'

/** 本地存储键：记录用户已关闭安装提示 */
const DISMISS_KEY = 'pwa-install-dismissed'

/**
 * PWA 安装提示组件。
 *
 * 当浏览器触发 beforeinstallprompt 且用户未关闭过提示时，
 * 显示一个可安装的横幅卡片，引导用户将应用安装到主屏幕。
 *
 * 行为：
 * - 用户点击"安装"后触发原生安装提示
 * - 用户点击关闭后，本次会话不再显示（并持久化到 localStorage）
 */
export function InstallPrompt() {
  const { canInstall, isInstalled, promptInstall } = usePWA()
  const { t } = useTranslation()
  const [dismissed, setDismissed] = useState(false)
  const [installing, setInstalling] = useState(false)

  // 从本地存储读取关闭状态
  useEffect(() => {
    if (typeof window === 'undefined') return
    try {
      setDismissed(window.localStorage.getItem(DISMISS_KEY) === '1')
    } catch {
      // localStorage 不可用时忽略
    }
  }, [])

  // 已安装、不可安装或已关闭时不渲染
  if (isInstalled || !canInstall || dismissed) return null

  const handleInstall = async () => {
    setInstalling(true)
    try {
      await promptInstall()
    } finally {
      setInstalling(false)
    }
  }

  const handleDismiss = () => {
    setDismissed(true)
    try {
      window.localStorage.setItem(DISMISS_KEY, '1')
    } catch {
      // localStorage 不可用时忽略
    }
  }

  return (
    <Card className="fixed bottom-4 left-4 right-4 sm:left-auto sm:right-4 sm:w-80 z-50 shadow-lg animate-slide-up">
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="rounded-md bg-primary/10 p-2">
            <Smartphone className="h-5 w-5 text-primary" />
          </div>
          <div className="flex-1 space-y-1">
            <p className="text-sm font-medium leading-tight">
              {t('common.theme')}
            </p>
            <p className="text-xs text-muted-foreground">
              {t('common.theme')}
            </p>
            <div className="flex gap-2 pt-2">
              <Button
                size="sm"
                onClick={handleInstall}
                disabled={installing}
                className="h-8"
              >
                <Download className="h-3.5 w-3.5 mr-1" />
                {installing ? '...' : t('common.confirm')}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleDismiss}
                className="h-8"
              >
                {t('common.cancel')}
              </Button>
            </div>
          </div>
          <Button
            size="icon"
            variant="ghost"
            className="h-6 w-6 shrink-0"
            onClick={handleDismiss}
            aria-label={t('common.cancel')}
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

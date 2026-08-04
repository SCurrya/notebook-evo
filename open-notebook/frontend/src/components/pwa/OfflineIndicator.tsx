'use client'

import { useEffect, useState } from 'react'
import { usePWA } from '@/lib/hooks/use-pwa'
import { WifiOff } from 'lucide-react'

/**
 * 离线指示器组件。
 *
 * 当检测到网络离线时，在页面顶部显示一个固定的提示条，
 * 告知用户当前处于离线状态，仅可访问已缓存的内容。
 * 恢复在线后自动隐藏。
 */
export function OfflineIndicator() {
  const { isOffline } = usePWA()
  const [visible, setVisible] = useState(false)

  // 延迟显示，避免短暂离线闪烁
  useEffect(() => {
    if (isOffline) {
      setVisible(true)
    } else {
      // 在线时短暂延迟后隐藏，让用户看到恢复提示
      const timer = window.setTimeout(() => setVisible(false), 1500)
      return () => window.clearTimeout(timer)
    }
  }, [isOffline])

  if (!visible) return null

  return (
    <div
      role="status"
      aria-live="polite"
      className={`fixed top-0 left-0 right-0 z-[60] flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white transition-all duration-300 ${
        isOffline
          ? 'bg-amber-600 animate-slide-down'
          : 'bg-emerald-600 animate-slide-up'
      }`}
    >
      <WifiOff className="h-4 w-4" />
      <span>
        {isOffline ? '当前处于离线状态，仅可访问已缓存内容' : '已恢复在线'}
      </span>
    </div>
  )
}

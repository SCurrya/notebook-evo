'use client'

import { useEffect } from 'react'

const LOCAL_DESKTOP_HOSTS = new Set(['127.0.0.1', 'localhost', '::1'])
const CACHE_PREFIX = 'open-notebook'

function isDesktopHost() {
  return (
    typeof window !== 'undefined' &&
    LOCAL_DESKTOP_HOSTS.has(window.location.hostname) &&
    window.location.port === '8502'
  )
}

async function clearDesktopCaches() {
  if ('serviceWorker' in navigator) {
    const registrations = await navigator.serviceWorker.getRegistrations()
    await Promise.all(registrations.map((registration) => registration.unregister()))
  }

  if ('caches' in window) {
    const cacheNames = await caches.keys()
    await Promise.all(
      cacheNames
        .filter((cacheName) => cacheName.startsWith(CACHE_PREFIX))
        .map((cacheName) => caches.delete(cacheName))
    )
  }
}

/**
 * Service Worker 注册组件。
 *
 * 在生产环境（非开发环境）中注册 /sw.js Service Worker，
 * 启用离线缓存与 stale-while-revalidate 策略。
 *
 * 注册失败时静默处理，不影响应用正常运行。
 * 该组件不渲染任何可见 UI。
 */
export function ServiceWorkerRegister() {
  useEffect(() => {
    if (isDesktopHost()) {
      clearDesktopCaches().catch((error) => {
        console.warn('桌面模式清理 Service Worker 缓存失败:', error)
      })
      return
    }

    // 仅在生产环境且浏览器支持 SW 时注册
    if (
      typeof window === 'undefined' ||
      !('serviceWorker' in navigator) ||
      process.env.NODE_ENV !== 'production'
    ) {
      return
    }

    const register = async () => {
      try {
        await navigator.serviceWorker.register('/sw.js', { scope: '/' })
      } catch (error) {
        // 注册失败时静默处理，不影响应用功能
        console.warn('Service Worker 注册失败:', error)
      }
    }

    // 等待页面加载完成后再注册，避免与首屏资源竞争带宽
    if (document.readyState === 'complete') {
      register()
    } else {
      window.addEventListener('load', register)
      return () => window.removeEventListener('load', register)
    }
  }, [])

  return null
}

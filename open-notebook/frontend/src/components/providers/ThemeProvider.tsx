'use client'

import { useEffect } from 'react'
import { useThemeStore } from '@/lib/stores/theme-store'

interface ThemeProviderProps {
  children: React.ReactNode
}

/**
 * 主题提供者组件
 *
 * 负责将主题状态同步到 document 根元素，并处理以下增强功能：
 * - 系统主题跟随：当主题设为 'system' 时，监听操作系统主题变化
 * - 过渡动画：主题切换时启用平滑的颜色过渡，避免突兀闪烁
 */
export function ThemeProvider({ children }: ThemeProviderProps) {
  const { theme, getSystemTheme, getEffectiveTheme } = useThemeStore()

  useEffect(() => {
    const root = window.document.documentElement
    const effectiveTheme = getEffectiveTheme()

    // 主题切换前：临时启用过渡动画类
    // 该类为所有颜色相关属性添加平滑过渡
    root.classList.add('theme-transition')

    // 移除旧主题类，应用新主题类
    root.classList.remove('light', 'dark')
    root.classList.add(effectiveTheme)
    root.setAttribute('data-theme', effectiveTheme)
    // 同步 color-scheme 以让原生控件（滚动条、表单元素）适配主题
    root.style.colorScheme = effectiveTheme

    // 过渡动画完成后移除过渡类，避免后续非主题相关的颜色变化产生动画
    const transitionTimer = window.setTimeout(() => {
      root.classList.remove('theme-transition')
    }, 400)

    return () => {
      window.clearTimeout(transitionTimer)
    }
  }, [theme, getSystemTheme, getEffectiveTheme])

  // 监听系统主题变化（仅在 'system' 模式下生效）
  useEffect(() => {
    if (theme !== 'system') return

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

    const handleChange = () => {
      const root = window.document.documentElement
      const newSystemTheme = getSystemTheme()

      // 启用过渡动画
      root.classList.add('theme-transition')

      root.classList.remove('light', 'dark')
      root.classList.add(newSystemTheme)
      root.setAttribute('data-theme', newSystemTheme)
      root.style.colorScheme = newSystemTheme

      const timer = window.setTimeout(() => {
        root.classList.remove('theme-transition')
      }, 400)

      return () => window.clearTimeout(timer)
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [theme, getSystemTheme])

  return <>{children}</>
}

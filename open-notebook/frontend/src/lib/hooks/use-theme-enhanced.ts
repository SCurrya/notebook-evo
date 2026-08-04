'use client'

import { useCallback, useEffect, useState } from 'react'
import { useThemeStore, type Theme } from '@/lib/stores/theme-store'

/**
 * 颜色预设类型。
 * 与 globals.css 中 [data-color-preset="..."] 选择器一一对应。
 */
export type ColorPreset =
  | 'indigo'
  | 'emerald'
  | 'amber'
  | 'rose'
  | 'ocean'

/** 颜色预设元数据，用于设置面板渲染。 */
export interface ColorPresetMeta {
  value: ColorPreset
  label: string
  /** 预设主色色块（CSS 颜色字符串） */
  swatch: string
}

/** 可用颜色预设列表。 */
export const COLOR_PRESETS: ColorPresetMeta[] = [
  { value: 'indigo', label: '靛紫', swatch: 'oklch(0.55 0.25 280)' },
  { value: 'emerald', label: '翡翠', swatch: 'oklch(0.62 0.19 155)' },
  { value: 'amber', label: '琥珀', swatch: 'oklch(0.75 0.18 70)' },
  { value: 'rose', label: '玫瑰', swatch: 'oklch(0.65 0.22 340)' },
  { value: 'ocean', label: '海洋', swatch: 'oklch(0.62 0.15 230)' },
]

const COLOR_PRESET_STORAGE_KEY = 'theme-color-preset'

/**
 * 读取本地存储的颜色预设。
 * 仅在客户端执行，返回默认值 'indigo' 当不可用或值非法时。
 */
function readStoredPreset(): ColorPreset {
  if (typeof window === 'undefined') return 'indigo'
  try {
    const raw = window.localStorage.getItem(COLOR_PRESET_STORAGE_KEY)
    if (raw) {
      const valid = COLOR_PRESETS.find((p) => p.value === raw)
      if (valid) return valid.value
    }
  } catch {
    // localStorage 不可用时忽略
  }
  return 'indigo'
}

/**
 * 将颜色预设应用到 document 根元素的 data-color-preset 属性。
 */
function applyColorPreset(preset: ColorPreset) {
  if (typeof window === 'undefined') return
  const root = window.document.documentElement
  root.setAttribute('data-color-preset', preset)
}

/**
 * 增强主题 Hook。
 *
 * 在 useThemeStore 基础上扩展：
 * - 颜色预设管理（持久化到 localStorage，同步到 data-color-preset 属性）
 * - 系统主题实时跟随（监听 prefers-color-scheme 变化）
 * - 便捷的派生状态（isDark / isSystem / systemTheme）
 *
 * 支持三种主题模式：light / dark / system
 */
export function useThemeEnhanced() {
  const { theme, setTheme } = useThemeStore()
  const [colorPreset, setColorPresetState] = useState<ColorPreset>('indigo')
  const [systemTheme, setSystemTheme] = useState<'light' | 'dark'>('light')

  // 初始化：从本地存储读取颜色预设并应用
  useEffect(() => {
    const stored = readStoredPreset()
    setColorPresetState(stored)
    applyColorPreset(stored)
  }, [])

  // 监听系统主题变化，同步本地状态（用于 system 模式下的实时跟随）
  useEffect(() => {
    if (typeof window === 'undefined') return
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    setSystemTheme(mediaQuery.matches ? 'dark' : 'light')

    const handleChange = (e: MediaQueryListEvent) => {
      setSystemTheme(e.matches ? 'dark' : 'light')
    }
    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])

  /**
   * 设置颜色预设并持久化。
   * 同步更新 document 的 data-color-preset 属性以触发 CSS 变量切换。
   */
  const setColorPreset = useCallback((preset: ColorPreset) => {
    setColorPresetState(preset)
    applyColorPreset(preset)
    try {
      window.localStorage.setItem(COLOR_PRESET_STORAGE_KEY, preset)
    } catch {
      // localStorage 不可用时忽略
    }
  }, [])

  const effectiveTheme = theme === 'system' ? systemTheme : theme

  return {
    /** 当前主题模式（light / dark / system） */
    theme,
    /** 设置主题模式 */
    setTheme,
    /** 当前生效的实际主题（system 模式下解析为 light / dark） */
    effectiveTheme,
    /** 系统当前主题偏好 */
    systemTheme,
    /** 是否为暗色模式 */
    isDark: effectiveTheme === 'dark',
    /** 是否处于系统跟随模式 */
    isSystem: theme === 'system',
    /** 当前颜色预设 */
    colorPreset,
    /** 设置颜色预设 */
    setColorPreset,
    /** 可用颜色预设列表 */
    colorPresets: COLOR_PRESETS,
  }
}

export type { Theme }

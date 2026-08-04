'use client'

import { useThemeEnhanced, type ColorPreset } from '@/lib/hooks/use-theme-enhanced'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Sun, Moon, Monitor, Check, Palette } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'

interface ThemeSettingsProps {
  /** 控制面板的打开状态 */
  open: boolean
  /** 打开状态变更回调 */
  onOpenChange: (open: boolean) => void
}

/**
 * 主题设置面板组件。
 *
 * 提供完整的主题配置入口：
 * - 主题模式选择（亮色 / 暗色 / 跟随系统）
 * - 颜色预设选择（靛紫 / 翡翠 / 琥珀 / 玫瑰 / 海洋）
 *
 * 颜色预设通过 data-color-preset 属性切换 CSS 变量，
 * 与 globals.css 中的预设定义对应。
 */
export function ThemeSettings({ open, onOpenChange }: ThemeSettingsProps) {
  const {
    theme,
    setTheme,
    effectiveTheme,
    systemTheme,
    colorPreset,
    setColorPreset,
    colorPresets,
  } = useThemeEnhanced()
  const { t } = useTranslation()

  // 主题模式选项
  const themeModes = [
    { value: 'light' as const, icon: Sun, label: t('common.light') },
    { value: 'dark' as const, icon: Moon, label: t('common.dark') },
    { value: 'system' as const, icon: Monitor, label: t('common.system') },
  ]

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Palette className="h-5 w-5" />
            {t('common.theme')}
          </DialogTitle>
          <DialogDescription>
            {t('common.theme')}
          </DialogDescription>
        </DialogHeader>

        {/* 主题模式选择 */}
        <div className="space-y-3">
          <Label className="text-sm font-medium">{t('common.theme')}</Label>
          <div className="grid grid-cols-3 gap-2">
            {themeModes.map((mode) => {
              const Icon = mode.icon
              const isActive = theme === mode.value
              return (
                <Button
                  key={mode.value}
                  variant={isActive ? 'default' : 'outline'}
                  size="sm"
                  className="flex flex-col items-center gap-1 h-auto py-3"
                  onClick={() => setTheme(mode.value)}
                >
                  <Icon className="h-4 w-4" />
                  <span className="text-xs">{mode.label}</span>
                  {isActive && <Check className="h-3 w-3" />}
                </Button>
              )
            })}
          </div>
          {/* 系统跟随模式下的状态提示 */}
          {theme === 'system' && (
            <p className="text-xs text-muted-foreground">
              {t('common.system')}: {systemTheme === 'dark' ? t('common.dark') : t('common.light')}
            </p>
          )}
        </div>

        {/* 颜色预设选择 */}
        <div className="space-y-3">
          <Label className="text-sm font-medium">{t('common.theme')}</Label>
          <div className="grid grid-cols-5 gap-2">
            {colorPresets.map((preset) => {
              const isActive = colorPreset === preset.value
              return (
                <button
                  key={preset.value}
                  type="button"
                  onClick={() => setColorPreset(preset.value as ColorPreset)}
                  className={`relative flex flex-col items-center gap-1 rounded-md border-2 p-2 transition-all hover:scale-105 ${
                    isActive ? 'border-primary' : 'border-transparent'
                  }`}
                  aria-label={preset.label}
                  aria-pressed={isActive}
                >
                  {/* 预设主色色块 */}
                  <span
                    className="h-8 w-8 rounded-full"
                    style={{ backgroundColor: preset.swatch }}
                  />
                  <span className="text-[10px] text-muted-foreground">
                    {preset.label}
                  </span>
                  {isActive && (
                    <Check className="absolute -top-1 -right-1 h-4 w-4 text-primary bg-background rounded-full" />
                  )}
                </button>
              )
            })}
          </div>
        </div>

        {/* 当前生效主题提示 */}
        <div className="flex items-center justify-between rounded-md bg-muted px-3 py-2 text-xs">
          <span className="text-muted-foreground">{t('common.theme')}</span>
          <span className="font-medium">
            {effectiveTheme === 'dark' ? t('common.dark') : t('common.light')}
          </span>
        </div>
      </DialogContent>
    </Dialog>
  )
}

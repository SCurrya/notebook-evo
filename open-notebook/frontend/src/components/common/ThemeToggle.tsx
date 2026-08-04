'use client'

import { useTheme } from '@/lib/stores/theme-store'
import { useThemeEnhanced } from '@/lib/hooks/use-theme-enhanced'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Sun, Moon, Monitor, Check } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'

interface ThemeToggleProps {
  iconOnly?: boolean
}

/**
 * 主题切换组件
 *
 * 提供亮色 / 暗色 / 跟随系统三种主题选项：
 * - 根据当前有效主题显示对应的图标（太阳/月亮）
 * - 下拉菜单中高亮当前选中的主题并显示勾选标记
 * - 系统跟随选项会显示当前检测到的系统主题偏好
 * - 支持仅图标模式（用于侧边栏紧凑布局）
 */
export function ThemeToggle({ iconOnly = false }: ThemeToggleProps) {
  const { theme, setTheme } = useTheme()
  const { systemTheme } = useThemeEnhanced()
  const { t } = useTranslation()

  // 主题选项配置
  const themeOptions = [
    { value: 'light' as const, icon: Sun, label: t('common.light') },
    { value: 'dark' as const, icon: Moon, label: t('common.dark') },
    { value: 'system' as const, icon: Monitor, label: t('common.system') },
  ]

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant={iconOnly ? 'ghost' : 'outline'}
          size={iconOnly ? 'icon' : 'default'}
          className={iconOnly ? 'h-9 w-full sidebar-menu-item' : 'w-full justify-start gap-2 sidebar-menu-item'}
        >
          <div className="relative h-[1.2rem] w-[1.2rem]">
            {/* 根据有效主题（而非用户选择）显示对应图标 */}
            <Sun className="absolute inset-0 h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all duration-300 dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute inset-0 h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all duration-300 dark:rotate-0 dark:scale-100" />
          </div>
          {!iconOnly && <span>{t('common.theme')}</span>}
          <span className="sr-only">{t('navigation.theme')}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>{t('common.theme')}</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {themeOptions.map((option) => {
          const Icon = option.icon
          const isActive = theme === option.value
          return (
            <DropdownMenuItem
              key={option.value}
              onClick={() => setTheme(option.value)}
              className={isActive ? 'bg-accent' : ''}
            >
              <Icon className="mr-2 h-4 w-4" />
              <span className="flex-1">{option.label}</span>
              {/* 系统跟随选项显示当前检测到的系统主题偏好 */}
              {option.value === 'system' && (
                <span className="text-xs text-muted-foreground mr-1">
                  ({systemTheme === 'dark' ? t('common.dark') : t('common.light')})
                </span>
              )}
              {/* 选中状态勾选标记 */}
              {isActive && <Check className="h-4 w-4 text-primary" />}
            </DropdownMenuItem>
          )
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

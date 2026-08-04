'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { usePathname } from 'next/navigation'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/hooks/use-auth'
import { useSidebarStore } from '@/lib/stores/sidebar-store'
import { useCreateDialogs } from '@/lib/hooks/use-create-dialogs'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ThemeToggle } from '@/components/common/ThemeToggle'
import { LanguageToggle } from '@/components/common/LanguageToggle'
import type { TFunction } from 'i18next'
import { useTranslation } from '@/lib/hooks/use-translation'
import { Separator } from '@/components/ui/separator'
import {
  Book,
  Search,
  Mic,
  Bot,
  Shuffle,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
  FileText,
  Plus,
  Wrench,
  Command,
  Sparkles,
  FileBarChart,
  HelpCircle,
  Clock,
  Network,
  KeyRound,
  Video,
  ScrollText,
  Cpu,
  Presentation,
  PenTool,
  FileDown,
  ImageIcon,
  Activity,
} from 'lucide-react'

const getNavigation = (t: TFunction) => [
  {
    title: t('navigation.collect'),
    items: [{ name: t('navigation.sources'), href: '/sources', icon: FileText }],
  },
  {
    title: t('navigation.process'),
    items: [
      { name: t('navigation.notebooks'), href: '/notebooks', icon: Book },
      { name: t('navigation.askAndSearch'), href: '/search', icon: Search },
      { name: '知识图谱', href: '/knowledge-graph', icon: Network },
      { name: 'RAG 评估', href: '/eval', icon: Activity },
    ],
  },
  {
    title: t('navigation.create'),
    items: [
      { name: t('navigation.podcasts'), href: '/podcasts', icon: Mic },
      { name: '视频生成', href: '/video', icon: Video },
      { name: 'PPT 生成', href: '/ppt', icon: Presentation },
      { name: '博客创作', href: '/blog', icon: PenTool },
      { name: 'PDF 生成', href: '/pdf', icon: FileDown },
      { name: '图片生成', href: '/image', icon: ImageIcon },
    ],
  },
  {
    title: t('navigation.studio'),
    items: [
      { name: t('navigation.studioHome'), href: '/studio', icon: Sparkles },
      { name: t('navigation.studioTemplates'), href: '/studio/templates', icon: FileText },
      { name: t('navigation.studioReport'), href: '/studio/report', icon: FileBarChart },
      { name: t('navigation.studioFAQ'), href: '/studio/faq', icon: HelpCircle },
      { name: t('navigation.studioTimeline'), href: '/studio/timeline', icon: Clock },
    ],
  },
  {
    title: t('navigation.manage'),
    items: [
      { name: t('navigation.models'), href: '/settings/api-keys', icon: Bot },
      { name: t('navigation.transformations'), href: '/transformations', icon: Shuffle },
      { name: t('navigation.settings'), href: '/settings', icon: Settings },
      { name: 'API 访问密钥', href: '/settings/api-access', icon: KeyRound },
      { name: t('navigation.advanced'), href: '/advanced', icon: Wrench },
    ],
  },
  {
    title: '系统',
    items: [
      { name: '多Agent系统', href: '/agents', icon: Cpu },
      { name: '系统日志', href: '/logs', icon: ScrollText },
    ],
  },
] as const

type CreateTarget = 'source' | 'notebook' | 'podcast'

export function AppSidebar() {
  const { t } = useTranslation()
  const navigation = getNavigation(t)
  const pathname = usePathname()
  const { logout } = useAuth()
  const { isCollapsed, toggleCollapse } = useSidebarStore()
  const { openSourceDialog, openNotebookDialog, openPodcastDialog } = useCreateDialogs()

  const [createMenuOpen, setCreateMenuOpen] = useState(false)
  const [isMac, setIsMac] = useState(true)

  useEffect(() => {
    setIsMac(navigator.platform.toLowerCase().includes('mac'))
  }, [])

  const handleCreateSelection = (target: CreateTarget) => {
    setCreateMenuOpen(false)

    if (target === 'source') {
      openSourceDialog()
    } else if (target === 'notebook') {
      openNotebookDialog()
    } else if (target === 'podcast') {
      openPodcastDialog()
    }
  }

  return (
    <TooltipProvider delayDuration={0}>
      <div
        className={cn(
          'app-sidebar flex h-full min-h-0 flex-col border-r transition-all duration-300 ease-emphasized overflow-hidden',
          isCollapsed ? 'w-16' : 'w-64'
        )}
      >
        <div
          className={cn(
            'relative flex h-16 shrink-0 items-center border-b border-sidebar-border/60',
            isCollapsed ? 'px-2' : 'px-3 justify-between'
          )}
        >
          {isCollapsed ? (
            <>
              <div className="flex w-full items-center justify-center pr-7">
                <div className="size-10 shrink-0 rounded-xl gradient-primary flex items-center justify-center elevation-2">
                  <Image src="/logo.svg" alt="Open Notebook" width={24} height={24} />
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleCollapse}
                className="absolute right-2 top-1/2 z-30 h-7 w-7 -translate-y-1/2 shrink-0 rounded-full border border-sidebar-border/70 bg-background/80 text-sidebar-foreground shadow-sm backdrop-blur hover:bg-sidebar-accent hover:text-sidebar-foreground"
                aria-label="Expand sidebar"
                title="Expand sidebar"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </>
          ) : (
            <>
              <div className="flex min-w-0 items-center gap-2.5">
                <div className="size-9 rounded-lg gradient-primary flex items-center justify-center elevation-1">
                  <Image src="/logo.svg" alt={t('common.appName')} width={20} height={20} />
                </div>
                <span className="truncate text-base font-semibold text-sidebar-foreground tracking-tight">
                  {t('common.appName')}
                </span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleCollapse}
                className="relative z-20 shrink-0 rounded-full border border-sidebar-border/70 text-sidebar-foreground hover:bg-sidebar-accent"
                data-testid="sidebar-toggle"
                aria-label="Collapse sidebar"
                title="Collapse sidebar"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>

        <div
          className={cn(
            'flex-1 min-h-0 overflow-y-auto overflow-x-hidden py-4 app-sidebar-scroll overscroll-contain',
            isCollapsed ? 'px-2 pr-1' : 'px-3 pr-2'
          )}
          style={{ scrollbarGutter: 'stable both-edges', WebkitOverflowScrolling: 'touch' }}
        >
          <div className={cn('mb-4', isCollapsed ? 'px-0' : 'px-3')}>
            <DropdownMenu open={createMenuOpen} onOpenChange={setCreateMenuOpen}>
              {isCollapsed ? (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <DropdownMenuTrigger asChild>
                      <Button
                        onClick={() => setCreateMenuOpen(true)}
                        variant="default"
                        size="sm"
                        className="w-full justify-center px-2 bg-primary hover:bg-primary/90 text-primary-foreground border-0 rounded-xl"
                        aria-label={t('common.create')}
                      >
                        <Plus className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                  </TooltipTrigger>
                  <TooltipContent side="right">{t('common.create')}</TooltipContent>
                </Tooltip>
              ) : (
                <DropdownMenuTrigger asChild>
                  <Button
                    onClick={() => setCreateMenuOpen(true)}
                    variant="gradient"
                    size="sm"
                    className="w-full justify-start text-primary-foreground border-0 elevation-2 hover:elevation-3 rounded-xl"
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    {t('common.create')}
                  </Button>
                </DropdownMenuTrigger>
              )}

              <DropdownMenuContent
                align={isCollapsed ? 'end' : 'start'}
                side={isCollapsed ? 'right' : 'bottom'}
                className="w-48"
              >
                <DropdownMenuItem
                  onSelect={(event) => {
                    event.preventDefault()
                    handleCreateSelection('source')
                  }}
                  className="gap-2"
                >
                  <FileText className="h-4 w-4" />
                  {t('common.source')}
                </DropdownMenuItem>
                <DropdownMenuItem
                  onSelect={(event) => {
                    event.preventDefault()
                    handleCreateSelection('notebook')
                  }}
                  className="gap-2"
                >
                  <Book className="h-4 w-4" />
                  {t('common.notebook')}
                </DropdownMenuItem>
                <DropdownMenuItem
                  onSelect={(event) => {
                    event.preventDefault()
                    handleCreateSelection('podcast')
                  }}
                  className="gap-2"
                >
                  <Mic className="h-4 w-4" />
                  {t('common.podcast')}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          {navigation.map((section, index) => (
            <div key={section.title}>
              {index > 0 && <Separator className="my-3" />}
              <div className="space-y-1">
                {!isCollapsed && (
                  <h3 className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-sidebar-foreground/60">
                    {section.title}
                  </h3>
                )}

                {section.items.map((item) => {
                  const isActive = pathname?.startsWith(item.href) || false
                  const button = (
                    <Button
                      variant={isActive ? 'secondary' : 'ghost'}
                      className={cn(
                        'w-full gap-3 text-sidebar-foreground sidebar-menu-item rounded-xl',
                        isActive && 'is-active bg-sidebar-accent text-sidebar-accent-foreground font-medium',
                        isCollapsed ? 'justify-center px-2' : 'justify-start'
                      )}
                    >
                      <item.icon className={cn('h-4 w-4 transition-transform', isActive && 'text-primary')} />
                      {!isCollapsed && <span>{item.name}</span>}
                    </Button>
                  )

                  if (isCollapsed) {
                    return (
                      <Tooltip key={item.name}>
                        <TooltipTrigger asChild>
                          <Link href={item.href}>{button}</Link>
                        </TooltipTrigger>
                        <TooltipContent side="right">{item.name}</TooltipContent>
                      </Tooltip>
                    )
                  }

                  return (
                    <Link key={item.name} href={item.href}>
                      {button}
                    </Link>
                  )
                })}
              </div>
            </div>
          ))}

          <div className="border-t border-sidebar-border/60 mt-4 pt-4 space-y-2">
            {!isCollapsed && (
              <div className="px-3 py-1.5 text-xs text-sidebar-foreground/60">
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <Command className="h-3 w-3" />
                    {t('common.quickActions')}
                  </span>
                  <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
                    {isMac ? <span className="text-xs">⌘</span> : <span>Ctrl+</span>}K
                  </kbd>
                </div>
                <p className="mt-1 text-[10px] text-sidebar-foreground/40">
                  {t('common.quickActionsDesc')}
                </p>
              </div>
            )}

            <div
              className={cn(
                'flex flex-col gap-2',
                isCollapsed ? 'items-center' : 'items-stretch'
              )}
            >
              {isCollapsed ? (
                <>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div>
                        <ThemeToggle iconOnly />
                      </div>
                    </TooltipTrigger>
                    <TooltipContent side="right">{t('common.theme')}</TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div>
                        <LanguageToggle iconOnly />
                      </div>
                    </TooltipTrigger>
                    <TooltipContent side="right">{t('common.language')}</TooltipContent>
                  </Tooltip>
                </>
              ) : (
                <>
                  <ThemeToggle />
                  <LanguageToggle />
                </>
              )}
            </div>

            {isCollapsed ? (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    className="w-full justify-center sidebar-menu-item rounded-xl"
                    onClick={logout}
                    aria-label={t('common.signOut')}
                  >
                    <LogOut className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">{t('common.signOut')}</TooltipContent>
              </Tooltip>
            ) : (
              <Button
                variant="outline"
                className="w-full justify-start gap-3 sidebar-menu-item rounded-xl"
                onClick={logout}
                aria-label={t('common.signOut')}
              >
                <LogOut className="h-4 w-4" />
                {t('common.signOut')}
              </Button>
            )}
          </div>
        </div>
      </div>
    </TooltipProvider>
  )
}

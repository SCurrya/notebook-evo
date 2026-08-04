'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { sourcesApi } from '@/lib/api/sources'
import { SourceListResponse } from '@/lib/types/api'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'
import { AppShell } from '@/components/layout/AppShell'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { FileText, Link as LinkIcon, Upload, AlignLeft, Trash2, ArrowUpDown } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getDateLocale } from '@/lib/utils/date-locale'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'
import { getApiErrorKey } from '@/lib/utils/error-handler'
import { PageHeader } from '@/components/ui/page-header'
import { navigateToStaticHref, sourceDetailHref } from '@/lib/routes'

export default function SourcesPage() {
  const { t, language } = useTranslation()
  const [sources, setSources] = useState<SourceListResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [sortBy, setSortBy] = useState<'created' | 'updated'>('updated')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; source: SourceListResponse | null }>({ open: false, source: null })
  const router = useRouter()
  const tableRef = useRef<HTMLTableElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const offsetRef = useRef(0)
  const loadingMoreRef = useRef(false)
  const hasMoreRef = useRef(true)
  const PAGE_SIZE = 30

  const fetchSources = useCallback(async (reset = false) => {
    try {
      if (!reset && (loadingMoreRef.current || !hasMoreRef.current)) {
        return
      }

      if (reset) {
        setLoading(true)
        offsetRef.current = 0
        setSources([])
        hasMoreRef.current = true
      } else {
        loadingMoreRef.current = true
        setLoadingMore(true)
      }

      const data = await sourcesApi.list({
        limit: PAGE_SIZE,
        offset: offsetRef.current,
        sort_by: sortBy,
        sort_order: sortOrder,
      })

      if (reset) {
        setSources(data)
      } else {
        setSources((prev) => [...prev, ...data])
      }

      const hasMoreData = data.length === PAGE_SIZE
      hasMoreRef.current = hasMoreData
      offsetRef.current += data.length
    } catch (err) {
      console.error('Failed to fetch sources:', err)
      setError(t('sources.failedToLoad'))
      toast.error(t('sources.failedToLoad'))
    } finally {
      setLoading(false)
      setLoadingMore(false)
      loadingMoreRef.current = false
    }
  }, [sortBy, sortOrder, t])

  useEffect(() => {
    fetchSources(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortBy, sortOrder])

  useEffect(() => {
    if (sources.length > 0 && tableRef.current) {
      tableRef.current.focus()
    }
  }, [sources])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (sources.length === 0) return

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          setSelectedIndex((prev) => {
            const newIndex = Math.min(prev + 1, sources.length - 1)
            setTimeout(() => scrollToSelectedRow(newIndex), 0)
            return newIndex
          })
          break
        case 'ArrowUp':
          e.preventDefault()
          setSelectedIndex((prev) => {
            const newIndex = Math.max(prev - 1, 0)
            setTimeout(() => scrollToSelectedRow(newIndex), 0)
            return newIndex
          })
          break
        case 'Enter':
          e.preventDefault()
          if (sources[selectedIndex]) {
            navigateToStaticHref(sourceDetailHref(sources[selectedIndex].id), router)
          }
          break
        case 'Home':
          e.preventDefault()
          setSelectedIndex(0)
          setTimeout(() => scrollToSelectedRow(0), 0)
          break
        case 'End':
          e.preventDefault()
          const lastIndex = sources.length - 1
          setSelectedIndex(lastIndex)
          setTimeout(() => scrollToSelectedRow(lastIndex), 0)
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [sources, selectedIndex, router])

  const scrollToSelectedRow = (index: number) => {
    const scrollContainer = scrollContainerRef.current
    if (!scrollContainer) return

    const rows = scrollContainer.querySelectorAll('tbody tr')
    const selectedRow = rows[index] as HTMLElement
    if (!selectedRow) return

    const containerRect = scrollContainer.getBoundingClientRect()
    const rowRect = selectedRow.getBoundingClientRect()

    if (rowRect.top < containerRect.top) {
      selectedRow.scrollIntoView({ behavior: 'smooth', block: 'start' })
    } else if (rowRect.bottom > containerRect.bottom) {
      selectedRow.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }

  useEffect(() => {
    const scrollContainer = scrollContainerRef.current
    if (!scrollContainer) return

    let scrollTimeout: NodeJS.Timeout | null = null

    const handleScroll = () => {
      if (scrollTimeout) clearTimeout(scrollTimeout)

      scrollTimeout = setTimeout(() => {
        if (!scrollContainerRef.current) return

        const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current
        const distanceFromBottom = scrollHeight - scrollTop - clientHeight

        if (distanceFromBottom < 200 && !loadingMoreRef.current && hasMoreRef.current) {
          fetchSources(false)
        }
      }, 100)
    }

    scrollContainer.addEventListener('scroll', handleScroll)
    handleScroll()

    return () => {
      scrollContainer.removeEventListener('scroll', handleScroll)
      if (scrollTimeout) {
        clearTimeout(scrollTimeout)
      }
    }
  }, [fetchSources, sources.length])

  const toggleSort = (field: 'created' | 'updated') => {
    if (sortBy === field) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(field)
      setSortOrder('desc')
    }
  }

  const getSourceIcon = (source: SourceListResponse) => {
    if (source.asset?.url) return <LinkIcon className="h-4 w-4" />
    if (source.asset?.file_path) return <Upload className="h-4 w-4" />
    return <AlignLeft className="h-4 w-4" />
  }

  const getSourceType = (source: SourceListResponse) => {
    if (source.asset?.url) return t('sources.type.link')
    if (source.asset?.file_path) return t('sources.type.file')
    return t('sources.type.text')
  }

  const handleRowClick = useCallback((index: number, sourceId: string) => {
    setSelectedIndex(index)
    navigateToStaticHref(sourceDetailHref(sourceId), router)
  }, [router])

  const handleDeleteClick = useCallback((e: React.MouseEvent, source: SourceListResponse) => {
    e.stopPropagation()
    setDeleteDialog({ open: true, source })
  }, [])

  const handleDeleteConfirm = async () => {
    if (!deleteDialog.source) return

    try {
      await sourcesApi.delete(deleteDialog.source.id)
      toast.success(t('sources.deleteSuccess'))
      setSources((prev) => prev.filter((s) => s.id !== deleteDialog.source?.id))
      setDeleteDialog({ open: false, source: null })
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }, message?: string }
      console.error('Failed to delete source:', error)
      toast.error(t(getApiErrorKey(error.response?.data?.detail || error.message)))
    }
  }

  if (loading) {
    return (
      <AppShell>
        <div className="flex h-full items-center justify-center">
          <LoadingSpinner />
        </div>
      </AppShell>
    )
  }

  if (error) {
    return (
      <AppShell>
        <div className="flex h-full items-center justify-center">
          <p className="text-red-500">{error}</p>
        </div>
      </AppShell>
    )
  }

  if (sources.length === 0) {
    return (
      <AppShell>
        <EmptyState icon={FileText} title={t('sources.noSourcesYet')} description={t('sources.allSourcesDescShort')} />
      </AppShell>
    )
  }

  return (
    <AppShell>
      <div className="flex flex-col h-full w-full animate-fade-in">
        <PageHeader
          title={t('sources.allSources')}
          description={t('sources.allSourcesDesc')}
          icon={FileText}
        />

        <div className="flex-1 page-container py-6 min-h-0">
          <div ref={scrollContainerRef} className="rounded-2xl border bg-card/85 overflow-auto elevation-1">
            <table ref={tableRef} tabIndex={0} className="w-full min-w-[800px] outline-none table-fixed">
              <colgroup>
                <col className="w-[120px]" />
                <col className="w-auto" />
                <col className="w-[140px]" />
                <col className="w-[100px]" />
                <col className="w-[100px]" />
                <col className="w-[100px]" />
              </colgroup>
              <thead className="sticky top-0 bg-background/95 backdrop-blur border-b z-10">
                <tr className="border-b bg-muted/50">
                  <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">{t('common.type')}</th>
                  <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">{t('common.title')}</th>
                  <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground hidden sm:table-cell">
                    <Button variant="ghost" size="sm" onClick={() => toggleSort('created')} className="h-8 px-2 hover:bg-muted rounded-lg">
                      {t('common.created_label')}
                      <ArrowUpDown className={cn('ml-2 h-3 w-3', sortBy === 'created' ? 'opacity-100' : 'opacity-30')} />
                      {sortBy === 'created' && <span className="ml-1 text-xs">{sortOrder === 'asc' ? '↑' : '↓'}</span>}
                    </Button>
                  </th>
                  <th className="h-12 px-4 text-center align-middle font-medium text-muted-foreground hidden md:table-cell">{t('sources.insights')}</th>
                  <th className="h-12 px-4 text-center align-middle font-medium text-muted-foreground hidden lg:table-cell">{t('sources.embedded')}</th>
                  <th className="h-12 px-4 text-right align-middle font-medium text-muted-foreground">{t('common.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((source, index) => {
                  const sourceHref = sourceDetailHref(source.id)
                  const sourceTitle = source.title || t('sources.untitledSource')

                  return (
                  <tr key={source.id} onClick={() => handleRowClick(index, source.id)} onMouseEnter={() => setSelectedIndex(index)} className={cn('relative border-b transition-colors cursor-pointer', selectedIndex === index ? 'bg-accent/60' : 'hover:bg-muted/45')}>
                    <td className="h-12 px-4">
                      <a
                        href={sourceHref}
                        aria-label={`Open source: ${sourceTitle}`}
                        className="absolute inset-0 z-10 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                        onClick={() => setSelectedIndex(index)}
                      />
                      <div className="flex items-center gap-2">
                        {getSourceIcon(source)}
                        <Badge variant="secondary" className="text-xs rounded-full">{getSourceType(source)}</Badge>
                      </div>
                    </td>
                    <td className="relative z-20 h-12 px-4 pointer-events-none">
                      <div className="flex flex-col overflow-hidden">
                        <span className="font-medium truncate">{sourceTitle}</span>
                        {source.asset?.url && <span className="text-xs text-muted-foreground truncate">{source.asset.url}</span>}
                      </div>
                    </td>
                    <td className="relative z-20 h-12 px-4 text-muted-foreground text-sm hidden sm:table-cell pointer-events-none">
                      {formatDistanceToNow(new Date(source.created), { addSuffix: true, locale: getDateLocale(language) })}
                    </td>
                    <td className="relative z-20 h-12 px-4 text-center hidden md:table-cell pointer-events-none">
                      <span className="text-sm font-medium">{source.insights_count || 0}</span>
                    </td>
                    <td className="relative z-20 h-12 px-4 text-center hidden lg:table-cell pointer-events-none">
                      <Badge variant={source.embedded ? 'default' : 'secondary'} className="text-xs rounded-full">{source.embedded ? t('sources.yes') : t('sources.no')}</Badge>
                    </td>
                    <td className="relative z-30 h-12 px-4 text-right">
                      <Button variant="ghost" size="icon" onClick={(e) => handleDeleteClick(e, source)} className="text-destructive hover:text-destructive rounded-full">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </td>
                  </tr>
                  )
                })}
                {loadingMore && (
                  <tr>
                    <td colSpan={6} className="h-16 text-center">
                      <div className="flex items-center justify-center">
                        <LoadingSpinner />
                        <span className="ml-2 text-muted-foreground">{t('sources.loadingMore')}</span>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={deleteDialog.open}
        onOpenChange={(open) => setDeleteDialog({ open, source: deleteDialog.source })}
        title={t('sources.delete')}
        description={t('sources.deleteConfirmWithTitle').replace('{title}', deleteDialog.source?.title || t('sources.untitledSource'))}
        confirmText={t('common.delete')}
        confirmVariant="destructive"
        onConfirm={handleDeleteConfirm}
      />
    </AppShell>
  )
}

'use client'

import { useMemo, useState } from 'react'

import { AppShell } from '@/components/layout/AppShell'
import { NotebookList } from './components/NotebookList'
import { Button } from '@/components/ui/button'
import { Plus, RefreshCw, Book, FileText, StickyNote, Archive } from 'lucide-react'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { CreateNotebookDialog } from '@/components/notebooks/CreateNotebookDialog'
import { Input } from '@/components/ui/input'
import { useTranslation } from '@/lib/hooks/use-translation'
import { PageHeader, StatCard } from '@/components/ui/page-header'

export default function NotebooksPage() {
  const { t } = useTranslation()
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const { data: notebooks, isLoading, refetch } = useNotebooks(false)
  const { data: archivedNotebooks } = useNotebooks(true)

  const normalizedQuery = searchTerm.trim().toLowerCase()

  const filteredActive = useMemo(() => {
    if (!notebooks) return undefined
    if (!normalizedQuery) return notebooks
    return notebooks.filter((n) => n.name.toLowerCase().includes(normalizedQuery))
  }, [notebooks, normalizedQuery])

  const filteredArchived = useMemo(() => {
    if (!archivedNotebooks) return undefined
    if (!normalizedQuery) return archivedNotebooks
    return archivedNotebooks.filter((n) => n.name.toLowerCase().includes(normalizedQuery))
  }, [archivedNotebooks, normalizedQuery])

  const hasArchived = (archivedNotebooks?.length ?? 0) > 0
  const isSearching = normalizedQuery.length > 0

  // 统计数据
  const totalSources = notebooks?.reduce((sum, n) => sum + (n.source_count || 0), 0) ?? 0
  const totalNotes = notebooks?.reduce((sum, n) => sum + (n.note_count || 0), 0) ?? 0

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto animate-fade-in">
        <PageHeader
          title={t('notebooks.title')}
          description={t('notebooks.description') || '管理和组织你的知识笔记本'}
          icon={Book}
          actions={
            <>
              <Button
                variant="outline"
                size="icon"
                onClick={() => refetch()}
                aria-label="Refresh"
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
              <Button variant="gradient" onClick={() => setCreateDialogOpen(true)}>
                <Plus className="h-4 w-4" />
                <span className="hidden sm:inline">{t('notebooks.newNotebook')}</span>
                <span className="sm:hidden">新建</span>
              </Button>
            </>
          }
          stats={
            <>
              <StatCard
                label="活跃笔记本"
                value={notebooks?.length ?? 0}
                icon={Book}
              />
              <StatCard
                label="已归档"
                value={archivedNotebooks?.length ?? 0}
                icon={Archive}
              />
              <StatCard
                label="总源数"
                value={totalSources}
                icon={FileText}
              />
              <StatCard
                label="总笔记数"
                value={totalNotes}
                icon={StickyNote}
              />
            </>
          }
        />

        <div className="page-container py-6 space-y-6">
          {/* 搜索栏 */}
          <div className="animate-slide-up">
            <Input
              id="notebook-search"
              name="notebook-search"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder={t('notebooks.searchPlaceholder')}
              autoComplete="off"
              aria-label={t('common.accessibility.searchNotebooks') || 'Search notebooks'}
              className="w-full h-11 text-base elevation-1"
            />
          </div>

          <div className="space-y-8">
            <NotebookList
              notebooks={filteredActive}
              isLoading={isLoading}
              title={t('notebooks.activeNotebooks')}
              emptyTitle={isSearching ? t('common.noMatches') : undefined}
              emptyDescription={isSearching ? t('common.tryDifferentSearch') : undefined}
              onAction={!isSearching ? () => setCreateDialogOpen(true) : undefined}
              actionLabel={!isSearching ? t('notebooks.newNotebook') : undefined}
            />

            {hasArchived && (
              <NotebookList
                notebooks={filteredArchived}
                isLoading={false}
                title={t('notebooks.archivedNotebooks')}
                collapsible
                emptyTitle={isSearching ? t('common.noMatches') : undefined}
                emptyDescription={isSearching ? t('common.tryDifferentSearch') : undefined}
              />
            )}
          </div>
        </div>
      </div>

      <CreateNotebookDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
      />
    </AppShell>
  )
}

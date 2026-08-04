'use client'

// Studio 模板管理页面
// 展示模板列表，支持创建、编辑、删除模板

import { useState } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { PageHeader } from '@/components/ui/page-header'
import { TemplateEditor } from '@/components/studio/TemplateEditor'
import {
  useStudioTemplates,
  useDeleteStudioTemplate,
} from '@/lib/hooks/use-studio'
import type { StudioTemplate } from '@/lib/api/studio'
import { Plus, Pencil, Trash2, RefreshCw, FileText } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { BookOpenText } from 'lucide-react'
import { StudioLayout } from '@/components/studio/StudioLayout'

export default function StudioTemplatesPage() {
  const { t } = useTranslation()
  const { data: templates, isLoading, refetch } = useStudioTemplates()
  const deleteTemplate = useDeleteStudioTemplate()

  const [editorOpen, setEditorOpen] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<StudioTemplate | undefined>()
  const [deleteTarget, setDeleteTarget] = useState<StudioTemplate | undefined>()

  const handleCreate = () => {
    setEditingTemplate(undefined)
    setEditorOpen(true)
  }

  const handleEdit = (template: StudioTemplate) => {
    setEditingTemplate(template)
    setEditorOpen(true)
  }

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return
    await deleteTemplate.mutateAsync(deleteTarget.id)
    setDeleteTarget(undefined)
  }

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto animate-fade-in">
        <PageHeader
          title={t('studio.templates')}
          description={t('studio.templatesDesc')}
          icon={BookOpenText}
          actions={
            <>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                <RefreshCw className="h-4 w-4" />
              </Button>
              <Button size="sm" onClick={handleCreate}>
                <Plus className="h-4 w-4 mr-1" />
                {t('studio.createNewTemplate')}
              </Button>
            </>
          }
        />

        <div className="page-container py-6 space-y-6">
          <StudioLayout>
            {isLoading ? (
              <div className="py-12 text-center text-muted-foreground">
                {t('common.loading')}
              </div>
            ) : !templates || templates.length === 0 ? (
              <Card className="rounded-[24px] border-border/70 bg-background/80 p-12 text-center shadow-none">
                <FileText className="mx-auto mb-3 h-12 w-12 opacity-50" />
                <p className="mb-4 text-muted-foreground">{t('studio.noTemplates')}</p>
                <Button size="sm" onClick={handleCreate}>
                  <Plus className="mr-1 h-4 w-4" />
                  {t('studio.createNewTemplate')}
                </Button>
              </Card>
            ) : (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                {templates.map((template) => (
                  <Card key={template.id} className="rounded-[24px] border-border/70 bg-background/80 p-5 shadow-none">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 space-y-1">
                        <h3 className="truncate text-base font-semibold">{template.name}</h3>
                        <span className="inline-block rounded-full border border-border/70 bg-muted/70 px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                          {template.output_format}
                        </span>
                      </div>
                      <div className="flex shrink-0 gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(template)}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDeleteTarget(template)}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </div>
                    {template.description && (
                      <p className="mt-3 line-clamp-2 text-sm leading-6 text-muted-foreground">
                        {template.description}
                      </p>
                    )}
                    <p className="mt-4 line-clamp-4 rounded-2xl border border-border/70 bg-muted/40 p-3 text-xs leading-5 text-muted-foreground">
                      {template.prompt}
                    </p>
                  </Card>
                ))}
              </div>
            )}
          </StudioLayout>
        </div>
      </div>

      <TemplateEditor
        open={editorOpen}
        onOpenChange={setEditorOpen}
        template={editingTemplate}
      />

      <AlertDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(undefined)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('studio.deleteConfirmTitle')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('studio.deleteConfirmDesc')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {t('common.delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppShell>
  )
}

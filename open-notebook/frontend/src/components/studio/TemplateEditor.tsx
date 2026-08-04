'use client'

// Studio 模板编辑器组件
// 用于创建和编辑自定义模板，支持名称、描述、提示词、输出格式的编辑

import { useEffect, useId } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { MarkdownEditor } from '@/components/ui/markdown-editor'
import {
  useCreateStudioTemplate,
  useUpdateStudioTemplate,
} from '@/lib/hooks/use-studio'
import type { StudioTemplate } from '@/lib/api/studio'
import { useQueryClient } from '@tanstack/react-query'
import { STUDIO_QUERY_KEYS } from '@/lib/hooks/use-studio'
import { useTranslation } from '@/lib/hooks/use-translation'

// 表单校验 schema
const templateSchema = z.object({
  name: z.string().min(1),
  description: z.string().optional(),
  prompt: z.string().min(1),
  output_format: z.string().optional(),
})

type TemplateFormData = z.infer<typeof templateSchema>

interface TemplateEditorProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  template?: StudioTemplate
}

export function TemplateEditor({ open, onOpenChange, template }: TemplateEditorProps) {
  const { t } = useTranslation()
  const nameId = useId()
  const descriptionId = useId()
  const promptId = useId()
  const outputFormatId = useId()
  const isEditing = Boolean(template)

  const createTemplate = useCreateStudioTemplate()
  const updateTemplate = useUpdateStudioTemplate()
  const queryClient = useQueryClient()

  const {
    control,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<TemplateFormData>({
    resolver: zodResolver(templateSchema),
    defaultValues: {
      name: '',
      description: '',
      prompt: '',
      output_format: 'markdown',
    },
  })

  // 当弹窗打开或模板变化时，重置表单
  useEffect(() => {
    if (!open) {
      reset({ name: '', description: '', prompt: '', output_format: 'markdown' })
      return
    }
    reset({
      name: template?.name ?? '',
      description: template?.description ?? '',
      prompt: template?.prompt ?? '',
      output_format: template?.output_format ?? 'markdown',
    })
  }, [open, template, reset])

  const onSubmit = async (data: TemplateFormData) => {
    if (template) {
      await updateTemplate.mutateAsync({
        id: template.id,
        data: {
          name: data.name,
          description: data.description || '',
          prompt: data.prompt,
          output_format: data.output_format || 'markdown',
        },
      })
      queryClient.invalidateQueries({
        queryKey: STUDIO_QUERY_KEYS.template(template.id),
      })
    } else {
      await createTemplate.mutateAsync({
        name: data.name,
        description: data.description || '',
        prompt: data.prompt,
        output_format: data.output_format || 'markdown',
      })
    }
    reset()
    onOpenChange(false)
  }

  const handleClose = () => {
    reset()
    onOpenChange(false)
  }

  const isSaving = template ? updateTemplate.isPending : createTemplate.isPending

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-3xl w-full max-h-[90vh] overflow-hidden p-0">
        <DialogTitle className="sr-only">
          {isEditing ? t('common.edit') : t('studio.createNewTemplate')}
        </DialogTitle>
        <DialogDescription className="sr-only">
          {isEditing ? t('studio.editTemplate') : t('studio.createNewTemplate')}
        </DialogDescription>
        <form onSubmit={handleSubmit(onSubmit)} className="flex h-full flex-col">
          <div className="border-b px-6 py-4 space-y-4">
            <div>
              <Label htmlFor={nameId} className="text-sm font-medium">
                {t('studio.templateName')}
              </Label>
              <Controller
                control={control}
                name="name"
                render={({ field }) => (
                  <Input
                    id={nameId}
                    {...field}
                    placeholder={t('studio.templateNamePlaceholder')}
                    autoComplete="off"
                  />
                )}
              />
              {errors.name && (
                <p className="text-sm text-red-600 mt-1">{errors.name.message}</p>
              )}
            </div>

            <div>
              <Label htmlFor={descriptionId} className="text-sm font-medium">
                {t('common.description')}
              </Label>
              <Controller
                control={control}
                name="description"
                render={({ field }) => (
                  <Textarea
                    id={descriptionId}
                    {...field}
                    placeholder={t('studio.templateDescriptionPlaceholder')}
                    rows={2}
                    autoComplete="off"
                  />
                )}
              />
            </div>

            <div>
              <Label htmlFor={outputFormatId} className="text-sm font-medium">
                {t('studio.outputFormat')}
              </Label>
              <Controller
                control={control}
                name="output_format"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger id={outputFormatId} className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="markdown">Markdown</SelectItem>
                      <SelectItem value="json">JSON</SelectItem>
                      <SelectItem value="text">Text</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-6 py-4">
            <Label htmlFor={promptId} className="text-sm font-medium">
              {t('studio.templatePrompt')}
            </Label>
            <Controller
              control={control}
              name="prompt"
              render={({ field }) => (
                <MarkdownEditor
                  key={template?.id ?? 'new-template'}
                  value={field.value}
                  onChange={field.onChange}
                  height={360}
                  placeholder={t('studio.templatePromptPlaceholder')}
                  className="rounded-md border"
                  textareaId={promptId}
                  name={field.name}
                />
              )}
            />
            {errors.prompt && (
              <p className="text-sm text-red-600 mt-1">{errors.prompt.message}</p>
            )}
          </div>

          <div className="border-t px-6 py-4 flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={handleClose}>
              {t('common.cancel')}
            </Button>
            <Button type="submit" disabled={isSaving}>
              {isSaving
                ? `${t('common.saving')}...`
                : isEditing
                  ? t('common.saveChanges')
                  : t('studio.createNewTemplate')}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

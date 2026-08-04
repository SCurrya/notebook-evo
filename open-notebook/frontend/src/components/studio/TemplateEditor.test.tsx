import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { TemplateEditor } from './TemplateEditor'
import { useCreateStudioTemplate, useUpdateStudioTemplate } from '@/lib/hooks/use-studio'
import type { StudioTemplate } from '@/lib/api/studio'

// Mock hooks
vi.mock('@/lib/hooks/use-studio')
vi.mock('@/lib/hooks/use-studio', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/hooks/use-studio')>()
  return {
    ...actual,
    useCreateStudioTemplate: vi.fn(),
    useUpdateStudioTemplate: vi.fn(),
    STUDIO_QUERY_KEYS: {
      templates: ['studio', 'templates'] as const,
      template: (id: string) => ['studio', 'templates', id] as const,
    },
  }
})

// Mock react-query
vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({
    invalidateQueries: vi.fn(),
  }),
}))

// Mock markdown editor to avoid complex rendering
vi.mock('@/components/ui/markdown-editor', () => ({
  MarkdownEditor: ({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder?: string }) => (
    <textarea
      data-testid="markdown-editor"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
    />
  ),
}))

// Mock use-translation (already mocked in setup, but ensure t returns keys)
vi.mock('@/lib/hooks/use-translation', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    language: 'en-US',
    setLanguage: vi.fn(),
  }),
}))

// Mock use-toast
vi.mock('@/lib/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}))

// Mock error-handler
vi.mock('@/lib/utils/error-handler', () => ({
  getApiErrorMessage: (_e: unknown, t: (k: string) => string) => t('common.error'),
}))

function createCreateMock() {
  return {
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
  } as unknown as ReturnType<typeof useCreateStudioTemplate>
}

function createUpdateMock() {
  return {
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
  } as unknown as ReturnType<typeof useUpdateStudioTemplate>
}

describe('TemplateEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useCreateStudioTemplate).mockReturnValue(createCreateMock())
    vi.mocked(useUpdateStudioTemplate).mockReturnValue(createUpdateMock())
  })

  it('renders form fields when open', () => {
    render(
      <TemplateEditor open={true} onOpenChange={vi.fn()} />
    )

    expect(screen.getByText('studio.templateName')).toBeInTheDocument()
    expect(screen.getByText('common.description')).toBeInTheDocument()
    expect(screen.getByText('studio.outputFormat')).toBeInTheDocument()
    expect(screen.getByText('studio.templatePrompt')).toBeInTheDocument()
  })

  it('shows create button text for new template', () => {
    render(
      <TemplateEditor open={true} onOpenChange={vi.fn()} />
    )

    // 使用 getByRole 精确匹配提交按钮
    expect(screen.getByRole('button', { name: 'studio.createNewTemplate' })).toBeInTheDocument()
  })

  it('shows save button text when editing existing template', () => {
    const existingTemplate: StudioTemplate = {
      id: 'studio_template:test123',
      name: '测试模板',
      description: '描述',
      prompt: '提示词',
      output_format: 'markdown',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    }

    render(
      <TemplateEditor open={true} onOpenChange={vi.fn()} template={existingTemplate} />
    )

    expect(screen.getByText('common.saveChanges')).toBeInTheDocument()
  })

  it('calls createTemplate on submit for new template', async () => {
    const createMock = createCreateMock()
    vi.mocked(useCreateStudioTemplate).mockReturnValue(createMock)
    const onOpenChange = vi.fn()

    render(
      <TemplateEditor open={true} onOpenChange={onOpenChange} />
    )

    // 填写名称
    const nameInput = screen.getByPlaceholderText('studio.templateNamePlaceholder')
    fireEvent.change(nameInput, { target: { value: '新模板' } })

    // 填写提示词
    const promptEditor = screen.getByTestId('markdown-editor')
    fireEvent.change(promptEditor, { target: { value: '测试提示词' } })

    // 提交表单
    const submitButton = screen.getByRole('button', { name: 'studio.createNewTemplate' })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(createMock.mutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          name: '新模板',
          prompt: '测试提示词',
        })
      )
    })
  })

  it('calls updateTemplate on submit for existing template', async () => {
    const updateMock = createUpdateMock()
    vi.mocked(useUpdateStudioTemplate).mockReturnValue(updateMock)
    const onOpenChange = vi.fn()

    const existingTemplate: StudioTemplate = {
      id: 'studio_template:test123',
      name: '原名称',
      description: '描述',
      prompt: '原提示词',
      output_format: 'markdown',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    }

    render(
      <TemplateEditor open={true} onOpenChange={onOpenChange} template={existingTemplate} />
    )

    // 修改名称
    const nameInput = screen.getByPlaceholderText('studio.templateNamePlaceholder')
    fireEvent.change(nameInput, { target: { value: '更新名称' } })

    // 提交表单
    const submitButton = screen.getByText('common.saveChanges')
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(updateMock.mutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 'studio_template:test123',
          data: expect.objectContaining({
            name: '更新名称',
          }),
        })
      )
    })
  })

  it('closes editor on cancel', () => {
    const onOpenChange = vi.fn()

    render(
      <TemplateEditor open={true} onOpenChange={onOpenChange} />
    )

    const cancelButton = screen.getByText('common.cancel')
    fireEvent.click(cancelButton)

    expect(onOpenChange).toHaveBeenCalledWith(false)
  })
})

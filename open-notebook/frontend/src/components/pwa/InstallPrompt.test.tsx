import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { InstallPrompt } from './InstallPrompt'

// Mock usePWA hook
const mockPromptInstall = vi.fn()
const mockUsePWA = vi.fn()

vi.mock('@/lib/hooks/use-pwa', () => ({
  usePWA: () => mockUsePWA(),
}))

// useTranslation is mocked globally in setup.ts (t returns the key string)

describe('InstallPrompt', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // 清理 localStorage 中的关闭标记
    window.localStorage.clear()
    mockPromptInstall.mockResolvedValue(false)
  })

  it('当不可安装时不应渲染任何内容', () => {
    mockUsePWA.mockReturnValue({
      canInstall: false,
      isInstalled: false,
      isOffline: false,
      hasUpdate: false,
      promptInstall: mockPromptInstall,
      applyUpdate: vi.fn(),
    })

    const { container } = render(<InstallPrompt />)
    expect(container).toBeEmptyDOMElement()
  })

  it('当可安装时应显示安装提示与按钮', () => {
    mockUsePWA.mockReturnValue({
      canInstall: true,
      isInstalled: false,
      isOffline: false,
      hasUpdate: false,
      promptInstall: mockPromptInstall,
      applyUpdate: vi.fn(),
    })

    render(<InstallPrompt />)

    // 应渲染确认（安装）与取消（关闭）按钮
    expect(screen.getByText('common.confirm')).toBeInTheDocument()
    expect(screen.getByText('common.cancel')).toBeInTheDocument()
  })

  it('点击关闭按钮后应隐藏提示并持久化到 localStorage', async () => {
    mockUsePWA.mockReturnValue({
      canInstall: true,
      isInstalled: false,
      isOffline: false,
      hasUpdate: false,
      promptInstall: mockPromptInstall,
      applyUpdate: vi.fn(),
    })

    const { container } = render(<InstallPrompt />)

    // 点击取消按钮关闭提示
    const cancelButton = screen.getByText('common.cancel')
    fireEvent.click(cancelButton)

    // 组件应不再渲染
    await waitFor(() => {
      expect(container).toBeEmptyDOMElement()
    })

    // localStorage 应记录关闭状态
    expect(window.localStorage.getItem('pwa-install-dismissed')).toBe('1')
  })

  it('点击安装按钮应调用 promptInstall', async () => {
    mockUsePWA.mockReturnValue({
      canInstall: true,
      isInstalled: false,
      isOffline: false,
      hasUpdate: false,
      promptInstall: mockPromptInstall,
      applyUpdate: vi.fn(),
    })

    render(<InstallPrompt />)

    const installButton = screen.getByText('common.confirm')
    fireEvent.click(installButton)

    await waitFor(() => {
      expect(mockPromptInstall).toHaveBeenCalledTimes(1)
    })
  })

  it('已安装时不应渲染安装提示', () => {
    mockUsePWA.mockReturnValue({
      canInstall: true,
      isInstalled: true,
      isOffline: false,
      hasUpdate: false,
      promptInstall: mockPromptInstall,
      applyUpdate: vi.fn(),
    })

    const { container } = render(<InstallPrompt />)
    expect(container).toBeEmptyDOMElement()
  })
})

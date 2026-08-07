import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface SidebarState {
  isCollapsed: boolean
  toggleCollapse: () => void
  setCollapsed: (collapsed: boolean) => void
  // 移动端抽屉（Drawer）状态：手机上没有常驻侧边栏，用汉堡按钮打开
  isMobileOpen: boolean
  setMobileOpen: (open: boolean) => void
}

export const useSidebarStore = create<SidebarState>()(
  persist(
    (set) => ({
      isCollapsed: false,
      toggleCollapse: () => set((state) => ({ isCollapsed: !state.isCollapsed })),
      setCollapsed: (collapsed) => set({ isCollapsed: collapsed }),
      isMobileOpen: false,
      setMobileOpen: (open) => set({ isMobileOpen: open }),
    }),
    {
      name: 'sidebar-storage',
    }
  )
)

import { DashboardRuntime } from '@/components/layout/DashboardRuntime'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <DashboardRuntime>{children}</DashboardRuntime>
}

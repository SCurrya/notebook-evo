import PageClient from './page-client'
import { DashboardRuntime } from '@/components/layout/DashboardRuntime'

export function generateStaticParams() {
  return [{ id: '_placeholder' }]
}

export default function Page() {
  return (
    <DashboardRuntime>
      <PageClient />
    </DashboardRuntime>
  )
}

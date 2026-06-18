import PageClient from './page-client'

export function generateStaticParams() {
  return [{ id: '_placeholder' }]
}

export default function Page() {
  return <PageClient />
}

export function notebookDetailHref(notebookId: string): string {
  return `/notebooks/detail?notebookId=${encodeURIComponent(notebookId)}`
}

export function sourceDetailHref(sourceId: string): string {
  return `/sources/detail?sourceId=${encodeURIComponent(sourceId)}`
}

interface RouterLike {
  push: (href: string) => void
}

export function navigateToStaticHref(href: string, router?: RouterLike): void {
  // Static exported App Router detail pages can fail client-side RSC navigation
  // under the desktop/static server. A full document navigation is slower but reliable.
  if (typeof window !== 'undefined') {
    window.location.assign(href)
    return
  }

  router?.push(href)
}

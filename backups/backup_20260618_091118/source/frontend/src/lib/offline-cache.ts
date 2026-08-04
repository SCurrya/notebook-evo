import { openDB, DBSchema, IDBPDatabase } from 'idb'

interface NotebookCache {
  id: string
  name: string
  description: string
  source_count: number
  note_count: number
  cached_at: number
}

interface OfflineDB extends DBSchema {
  notebooks: {
    key: string
    value: NotebookCache
    indexes: { 'by-cached': number }
  }
  sources: {
    key: string
    value: any
    indexes: { 'by-notebook': string }
  }
}

let dbPromise: Promise<IDBPDatabase<OfflineDB>> | null = null

function getDB(): Promise<IDBPDatabase<OfflineDB>> {
  if (!dbPromise) {
    dbPromise = openDB<OfflineDB>('open-notebook-offline', 1, {
      upgrade(db) {
        const notebookStore = db.createObjectStore('notebooks', { keyPath: 'id' })
        notebookStore.createIndex('by-cached', 'cached_at')
        const sourceStore = db.createObjectStore('sources', { keyPath: 'id' })
        sourceStore.createIndex('by-notebook', 'notebooks')
      },
    })
  }
  return dbPromise
}

export async function cacheNotebooks(notebooks: any[]): Promise<void> {
  try {
    const db = await getDB()
    const tx = db.transaction('notebooks', 'readwrite')
    const now = Date.now()
    await Promise.all(
      notebooks.map(n => tx.store.put({ ...n, cached_at: now }))
    )
    await tx.done
  } catch (e) {
    console.error('[OfflineCache] Failed to cache notebooks:', e)
  }
}

export async function getCachedNotebooks(): Promise<NotebookCache[]> {
  try {
    const db = await getDB()
    const all = await db.getAllFromIndex('notebooks', 'by-cached')
    return all.sort((a, b) => b.cached_at - a.cached_at)
  } catch (e) {
    console.error('[OfflineCache] Failed to read cached notebooks:', e)
    return []
  }
}

export async function cacheSources(notebookId: string, sources: any[]): Promise<void> {
  try {
    const db = await getDB()
    const tx = db.transaction('sources', 'readwrite')
    await Promise.all(
      sources.map(s => tx.store.put({ ...s, notebooks: [notebookId] }))
    )
    await tx.done
  } catch (e) {
    console.error('[OfflineCache] Failed to cache sources:', e)
  }
}

export async function getCachedSources(notebookId: string): Promise<any[]> {
  try {
    const db = await getDB()
    return await db.getAllFromIndex('sources', 'by-notebook', notebookId)
  } catch (e) {
    console.error('[OfflineCache] Failed to read cached sources:', e)
    return []
  }
}

export function isOfflineError(error: any): boolean {
  return error?.message?.startsWith('OFFLINE:') ||
         error?.message?.includes('Could not reach any API endpoint')
}

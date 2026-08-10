import { useCallback, useState } from 'react'

const STORAGE_KEY = 'open-notebook-search-history'
const MAX_ITEMS = 8

interface SearchHistoryEntry {
  query: string
  mode: 'ask' | 'search'
  ts: number
}

function readHistory(): SearchHistoryEntry[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeHistory(entries: SearchHistoryEntry[]) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(entries.slice(0, MAX_ITEMS)))
  } catch {
    // ignore quota / privacy-mode errors
  }
}

/** 持久化的搜索/问答历史，用于快速重现之前的问题。 */
export function useSearchHistory() {
  const [history, setHistory] = useState<SearchHistoryEntry[]>(() => readHistory())

  const addHistory = useCallback((query: string, mode: 'ask' | 'search') => {
    const q = query.trim()
    if (!q) return
    setHistory((prev) => {
      const next = [{ query: q, mode, ts: Date.now() }, ...prev.filter((e) => e.query !== q)]
      writeHistory(next)
      return next.slice(0, MAX_ITEMS)
    })
  }, [])

  const clearHistory = useCallback(() => {
    setHistory([])
    writeHistory([])
  }, [])

  return { history, addHistory, clearHistory }
}

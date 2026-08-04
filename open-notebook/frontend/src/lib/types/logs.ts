/**
 * Log management types.
 */

export type LogLevel =
  | 'TRACE'
  | 'DEBUG'
  | 'INFO'
  | 'SUCCESS'
  | 'WARNING'
  | 'ERROR'
  | 'CRITICAL'

export interface LogEntry {
  timestamp: string | null
  level: string | null
  message: string
  raw: string
  line_number: number
}

export interface LogFile {
  name: string
  size: number
  modified: string | null
  line_count?: number | null
}

export interface ClearLogResult {
  filename?: string
  cleared: boolean
  bytes_freed: number
}

export interface ClearAllLogsResult {
  cleared_files: string[]
  count: number
  bytes_freed: number
}

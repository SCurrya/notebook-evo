/**
 * Unified frontend logging utility for Open Notebook.
 *
 * Provides structured console logging with log levels and production filtering.
 * In production, only WARN and above are output.
 *
 * Usage:
 *   import { logger } from '@/lib/utils/logger';
 *   logger.info('Notebook loaded', { notebookId: '123' });
 *   logger.error('Failed to save', { error: err });
 */

export type LogLevel = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR';

const LEVEL_PRIORITY: Record<LogLevel, number> = {
  DEBUG: 10,
  INFO: 20,
  WARN: 30,
  ERROR: 40,
};

function isProduction(): boolean {
  if (typeof process !== 'undefined' && process.env) {
    return process.env.NODE_ENV === 'production';
  }
  return false;
}

/** Minimum level to output. Production defaults to WARN, development to DEBUG. */
const MIN_LEVEL: LogLevel = isProduction() ? 'WARN' : 'DEBUG';

function shouldLog(level: LogLevel): boolean {
  return LEVEL_PRIORITY[level] >= LEVEL_PRIORITY[MIN_LEVEL];
}

function formatTimestamp(): string {
  return new Date().toISOString();
}

function formatMessage(
  level: LogLevel,
  module: string,
  operation: string,
  message: string,
  params?: Record<string, unknown>
): string {
  const paramsStr = params
    ? Object.entries(params)
        .map(([k, v]) => {
          const val = typeof v === 'string' ? v : JSON.stringify(v);
          const truncated =
            val.length > 200 ? val.slice(0, 200) + '...[truncated]' : val;
          return `${k}=${truncated}`;
        })
        .join(' ')
    : '-';
  return `${formatTimestamp()} | ${level} | ${module} | ${operation} | ${paramsStr} | ${message}`;
}

function consoleLog(level: LogLevel, formatted: string, extra?: unknown) {
  switch (level) {
    case 'DEBUG':
      console.debug(formatted, extra ?? '');
      break;
    case 'INFO':
      console.info(formatted, extra ?? '');
      break;
    case 'WARN':
      console.warn(formatted, extra ?? '');
      break;
    case 'ERROR':
      console.error(formatted, extra ?? '');
      break;
  }
}

export interface Logger {
  debug(message: string, params?: Record<string, unknown>): void;
  info(message: string, params?: Record<string, unknown>): void;
  warn(message: string, params?: Record<string, unknown>): void;
  error(message: string, params?: Record<string, unknown>): void;
}

/**
 * Create a logger bound to a module and operation context.
 *
 * @param module - Module name (e.g. 'notebooks', 'sources', 'chat')
 * @param operation - Operation type (e.g. 'CREATE', 'READ', 'UPDATE', 'DELETE')
 */
export function createLogger(
  module: string = '-',
  operation: string = '-'
): Logger {
  const log = (
    level: LogLevel,
    message: string,
    params?: Record<string, unknown>
  ) => {
    if (!shouldLog(level)) return;
    const formatted = formatMessage(level, module, operation, message, params);
    consoleLog(level, formatted);
  };

  return {
    debug: (msg, params) => log('DEBUG', msg, params),
    info: (msg, params) => log('INFO', msg, params),
    warn: (msg, params) => log('WARN', msg, params),
    error: (msg, params) => log('ERROR', msg, params),
  };
}

/** Default logger with no module/operation context. */
export const logger: Logger = createLogger();

/** Standard operation type constants for consistent tagging. */
export const Operation = {
  CREATE: 'CREATE',
  READ: 'READ',
  UPDATE: 'UPDATE',
  DELETE: 'DELETE',
  SEARCH: 'SEARCH',
  TRANSFORM: 'TRANSFORM',
  CHAT: 'CHAT',
} as const;

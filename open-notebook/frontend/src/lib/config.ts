/**
 * Runtime configuration for the frontend.
 * This allows the same Docker image to work in different environments.
 */

import { AppConfig, BackendConfigResponse } from '@/lib/types/config'
import { discoverApiUrl, isCapacitor, isMobileBuild } from '@/lib/api-discovery'

// Build timestamp for debugging - set at build time
const BUILD_TIME = new Date().toISOString()

let config: AppConfig | null = null
let configPromise: Promise<AppConfig> | null = null

async function fetchBackendConfig(apiUrl: string): Promise<AppConfig> {
  // Desktop EXE builds may serve the config payload from /config instead of /api/config.
  // Try both so the same frontend bundle works in the packaged app and web/mobile builds.
  const endpoints = [`${apiUrl}/api/config`, `${apiUrl}/config`]
  let lastError: unknown = null

  for (const endpoint of endpoints) {
    try {
      const response = await fetch(endpoint, {
        cache: 'no-store',
      })

      if (response.ok) {
        const data: BackendConfigResponse = await response.json()
        return {
          apiUrl,
          version: data.version || 'unknown',
          buildTime: BUILD_TIME,
          latestVersion: data.latestVersion || null,
          hasUpdate: data.hasUpdate || false,
          dbStatus: data.dbStatus,
        }
      }

      lastError = new Error(`API config endpoint returned status ${response.status}`)
    } catch (error) {
      lastError = error
    }
  }

  if (lastError instanceof Error) {
    throw lastError
  }
  throw new Error('Unable to load backend config')
}

/**
 * Get the API URL to use for requests.
 *
 * Priority:
 * 1. Runtime config from API server (/api/config endpoint)
 * 2. Environment variable (NEXT_PUBLIC_API_URL)
 * 3. Default fallback (http://localhost:5055)
 */
export async function getApiUrl(): Promise<string> {
  // If we already have config, return it
  if (config) {
    return config.apiUrl
  }

  // If we're already fetching, wait for that
  if (configPromise) {
    const cfg = await configPromise
    return cfg.apiUrl
  }

  // Start fetching config
  configPromise = fetchConfig()
  const cfg = await configPromise
  return cfg.apiUrl
}

/**
 * Get the full configuration.
 */
export async function getConfig(): Promise<AppConfig> {
  if (config) {
    return config
  }

  if (configPromise) {
    return await configPromise
  }

  configPromise = fetchConfig()
  return await configPromise
}

/**
 * Fetch configuration from the API or use defaults.
 */
async function fetchConfig(): Promise<AppConfig> {
  const isDev = process.env.NODE_ENV === 'development'

  if (isDev) {
    console.log('🔧 [Config] Starting configuration detection...')
    console.log('🔧 [Config] Build time:', BUILD_TIME)
  }

  // Mobile (Capacitor) path: discover API URL at runtime.
  // Static export has no Next.js server, so /config endpoint and rewrites are unavailable.
  if (isMobileBuild() || isCapacitor()) {
    if (isDev) console.log('🔧 [Config] Mobile build detected, discovering API URL at runtime...')
    const mobileApiUrl = await discoverApiUrl()
    if (!mobileApiUrl) {
      throw new Error('OFFLINE: Could not reach any API endpoint')
    }
    if (isDev) console.log('✅ [Config] Discovered mobile API URL:', mobileApiUrl)

    try {
      config = await fetchBackendConfig(mobileApiUrl)
      if (isDev) console.log('✅ [Config] Successfully loaded mobile API config:', config)
      return config
    } catch (error) {
      if (isDev) console.log('⚠️ [Config] Failed to fetch mobile backend config:', error)
      throw error
    }
  }

  // STEP 1: Try to get runtime config from Next.js server-side endpoint
  // This allows API_URL to be set at runtime (not baked into build)
  // Note: Endpoint is at /config (not /api/config) to avoid reverse proxy conflicts
  let runtimeApiUrl: string | null = null
  try {
    if (isDev) console.log('🔧 [Config] Attempting to fetch runtime config from /config endpoint...')
    const runtimeResponse = await fetch('/config', {
      cache: 'no-store',
    })
    if (runtimeResponse.ok) {
      const runtimeData = await runtimeResponse.json()
      runtimeApiUrl = runtimeData.apiUrl
      // Treat empty string as "not set" to allow fallback to env var or default
      if (runtimeApiUrl === '') {
        runtimeApiUrl = null
      }
      if (isDev) console.log('✅ [Config] Runtime API URL from server:', runtimeApiUrl)
    } else {
      if (isDev) console.log('⚠️ [Config] Runtime config endpoint returned status:', runtimeResponse.status)
    }
  } catch (error) {
    if (isDev) console.log('⚠️ [Config] Could not fetch runtime config:', error)
  }

  // STEP 2: Fallback to build-time environment variable
  const envApiUrl = process.env.NEXT_PUBLIC_API_URL
  if (isDev) console.log('🔧 [Config] NEXT_PUBLIC_API_URL from build:', envApiUrl || '(not set)')

  // STEP 3: Smart default - prefer relative path to use Next.js Rewrites
  // This avoids CORS issues and port mapping complexities by proxying through Next.js
  const defaultApiUrl = ''

  if (typeof window !== 'undefined' && isDev) {
      console.log('🔧 [Config] Using relative path (rewrites) as default')
  }

  // Priority: Runtime config > Build-time env var > Smart default
  // Note: runtimeApiUrl must be checked against null explicitly as empty string might be valid if intended (though we treat '' as null above)
  const baseUrl = runtimeApiUrl !== null && runtimeApiUrl !== undefined ? runtimeApiUrl : (envApiUrl || defaultApiUrl)
  if (isDev) {
    console.log('🔧 [Config] Final base URL to try:', baseUrl)
    console.log('🔧 [Config] Selection priority: runtime=' + (runtimeApiUrl ? '✅' : '❌') +
                ', build-time=' + (envApiUrl ? '✅' : '❌') +
                ', smart-default=' + (!runtimeApiUrl && !envApiUrl ? '✅' : '❌'))
  }

  // Try both endpoint conventions (/api/config and /config) to support
  // both current backend (path is /api/config) and older/alternative builds
  // (path is /config).
  const configEndpoints = [
    `${baseUrl}/api/config`,
    `${baseUrl}/config`,
  ]

  let lastError: unknown = null
  for (const endpoint of configEndpoints) {
    try {
      if (isDev) console.log('🔧 [Config] Fetching backend config from:', endpoint)
      const response = await fetch(endpoint, {
        cache: 'no-store',
      })

      if (response.ok) {
        const data: BackendConfigResponse = await response.json()
        config = {
          apiUrl: baseUrl,
          version: data.version || 'unknown',
          buildTime: BUILD_TIME,
          latestVersion: data.latestVersion || null,
          hasUpdate: data.hasUpdate || false,
          dbStatus: data.dbStatus,
        }
        if (isDev) console.log('✅ [Config] Successfully loaded API config:', config)
        return config
      }
      lastError = new Error(`API config endpoint returned status ${response.status}`)
    } catch (error) {
      lastError = error
    }
  }
  throw lastError ?? new Error('No config endpoint responded')
}

/**
 * Reset the configuration cache (useful for testing).
 */
export function resetConfig(): void {
  config = null
  configPromise = null
}

/**
 * Mobile app API domain discovery.
 * Tries multiple endpoints in priority order, returns first reachable one.
 * Used only in Capacitor (mobile) environment.
 */

const DISCOVERY_TIMEOUT = 3000 // 3 seconds per endpoint

// Candidate API URLs in priority order
function getCandidateUrls(): string[] {
  const candidates: string[] = []

  // 1. localhost (works in Android emulator, 10.0.2.2 maps to host)
  candidates.push('http://10.0.2.2:5055')
  candidates.push('http://localhost:5055')

  // 2. Hardcoded stable IPs (LAN + Tailscale) - always try these
  // LAN direct API (same WiFi, fastest)
  candidates.push('http://192.168.5.22:5055')
  // LAN via Caddy (Caddy adds CORS headers + serves /health)
  candidates.push('http://192.168.5.22:8889')
  // Tailscale direct API (works anywhere with Tailscale VPN)
  candidates.push('http://100.108.217.19:5055')
  // Tailscale via Caddy
  candidates.push('http://100.108.217.19:8889')

  // 3. Tailscale domain (set via env at build time or localStorage)
  const tailscaleDomain = process.env.NEXT_PUBLIC_TAILSCALE_DOMAIN
  if (tailscaleDomain) {
    candidates.push(`http://${tailscaleDomain}:5055`)
  }
  // Also check localStorage for runtime-configured domain
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem('tailscale-domain')
    if (stored) candidates.push(`http://${stored}:5055`)
  }

  // 4. Cloudflare Tunnel (HTTPS)
  const cloudflareDomain = process.env.NEXT_PUBLIC_CLOUDFLARE_DOMAIN
  if (cloudflareDomain) {
    candidates.push(`https://${cloudflareDomain}`)
  }
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem('cloudflare-domain')
    if (stored) candidates.push(`https://${stored}`)
  }

  return candidates
}

async function checkEndpoint(url: string): Promise<boolean> {
  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), DISCOVERY_TIMEOUT)
    const response = await fetch(`${url}/health`, {
      signal: controller.signal,
      mode: 'cors',
    })
    clearTimeout(timeout)
    return response.ok
  } catch {
    return false
  }
}

let discoveredUrl: string | null = null
let discoveryPromise: Promise<string | null> | null = null

export async function discoverApiUrl(): Promise<string | null> {
  if (discoveredUrl) return discoveredUrl

  if (discoveryPromise) return discoveryPromise
  discoveryPromise = (async () => {
    const candidates = getCandidateUrls()
    for (const url of candidates) {
      if (await checkEndpoint(url)) {
        discoveredUrl = url
        return url
      }
    }
    return null
  })()
  return discoveryPromise
}

export function resetDiscovery(): void {
  discoveredUrl = null
  discoveryPromise = null
}

export function isCapacitor(): boolean {
  return typeof window !== 'undefined' &&
         (window as any).Capacitor?.isNativePlatform?.() === true
}

export function isMobileBuild(): boolean {
  return process.env.BUILD_TARGET === 'mobile'
}

import type { NextConfig } from "next";

const isMobile = process.env.BUILD_TARGET === 'mobile'

const nextConfig: NextConfig = {
  // Mobile build uses static export for Capacitor; web build uses standalone for Docker
  output: isMobile ? "export" : "standalone",

  // Mobile build: skip type checking (faster builds, avoids dependency type issues)
  // Desktop build: also skip type checking due to csstype dependency type issue
  typescript: isMobile ? { ignoreBuildErrors: true } : { ignoreBuildErrors: true },

  // Allow dev server access from 127.0.0.1 and LAN IPs
  // (Next.js 16+ blocks cross-origin dev resource requests by default)
  allowedDevOrigins: ['127.0.0.1', 'localhost', '0.0.0.0'],

  // Static export (mobile) does not support image optimization
  images: isMobile ? { unoptimized: true } : undefined,

  // Capacitor requires trailing slashes for file-based routing to work correctly
  trailingSlash: isMobile ? true : undefined,

  // Experimental features
  // Type assertion needed: proxyClientMaxBodySize is valid in Next.js 15 but types lag behind
  experimental: {
    // Increase proxy body size limit for file uploads (default is 10MB)
    // This allows larger files to be uploaded through the /api/* rewrite proxy to FastAPI
    proxyClientMaxBodySize: '100mb',
  } as NextConfig['experimental'],

  // API Rewrites: Proxy /api/* requests to FastAPI backend
  // This simplifies reverse proxy configuration - users only need to proxy to port 8502
  // Next.js handles internal routing to the API backend on port 5055
  async rewrites() {
    // Static export (mobile) does not support rewrites - mobile app discovers API at runtime
    if (isMobile) return []

    // INTERNAL_API_URL: Where Next.js server-side should proxy API requests
    // Default: http://localhost:5055 (single-container deployment)
    // Override for multi-container: INTERNAL_API_URL=http://api-service:5055
    const internalApiUrl = process.env.INTERNAL_API_URL || 'http://localhost:5055'

    console.log(`[Next.js Rewrites] Proxying /api/* to ${internalApiUrl}/api/*`)

    return [
      {
        source: '/api/:path*',
        destination: `${internalApiUrl}/api/:path*`,
      },
    ]
  },
};

export default nextConfig;

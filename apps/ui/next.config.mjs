/** @type {import('next').NextConfig} */
const isDev = process.env.NODE_ENV === 'development';

const nextConfig = {
  // Enable standalone output for Docker builds (Dockerfile.ui)
  output: process.env.NEXT_OUTPUT === 'standalone' ? 'standalone' : undefined,
  ...(isDev ? { experimental: { allowedDevHosts: ['trycloudflare.com', '.trycloudflare.com'] } } : {}),
  compress: true,
  poweredByHeader: false,

  // Image optimisation — unoptimized:true disables the built-in optimizer;
  // keep it only when the CDN handles it (e.g. Cloudflare Images / Imgix).
  // Set NEXT_IMAGES_UNOPTIMIZED=true to revert to the old behaviour.
  images: {
    unoptimized: true,
    formats: ['image/avif', 'image/webp'],
    remotePatterns: [
      { protocol: 'https', hostname: 'v3b.fal.media' },
    ],
  },

  // Security + cache headers
  async headers() {
    return [
      {
        // Apply security headers to all routes
        source: '/(.*)',
        headers: [
          // Prevent MIME-type sniffing
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          // Prevent embedding in iframes (clickjacking)
          { key: 'X-Frame-Options', value: 'DENY' },
          // Stop legacy XSS filter from breaking things; CSP handles it
          { key: 'X-XSS-Protection', value: '0' },
          // Only send origin when navigating to HTTPS
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          // Allow fonts/scripts from same origin + Google Fonts; block everything else
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval' https://unpkg.com" : ''}`,
              "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
              "font-src 'self' https://fonts.gstatic.com",
              "img-src 'self' data: blob: https:",
              "connect-src 'self' https: wss:",
              "worker-src 'self' blob:",
              "frame-ancestors 'none'",
            ].join('; '),
          },
          // HSTS — 1 year, include subdomains
          { key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains' },
          // Permissions policy — disable unnecessary browser features
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=(), interest-cohort=()',
          },
        ],
      },
      {
        // Aggressive caching for Next.js static chunks (hashed filenames)
        source: '/_next/static/(.*)',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=31536000, immutable' },
        ],
      },
      {
        // Short cache for HTML pages — let CDN revalidate quickly
        source: '/((?!_next/static|_next/image|favicon.ico).*)',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=0, must-revalidate' },
        ],
      },
      {
        // Cache public assets (icons, images, fonts) for 7 days
        source: '/icons/(.*)',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=604800, stale-while-revalidate=86400' },
        ],
      },
    ];
  },

  async rewrites() {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${apiBase}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;

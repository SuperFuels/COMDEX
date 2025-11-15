// frontend/next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  trailingSlash: true,
  images: { unoptimized: true },
  eslint: { ignoreDuringBuilds: true },

  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || '',
    // NEW: where your radio-node is hosted (e.g. https://radio-node.yourdomain.com)
    NEXT_PUBLIC_RADIO_BASE: process.env.NEXT_PUBLIC_RADIO_BASE || '',
    // NEW: 'site' (default) navigates within website; 'spa' jumps to #/container/<id>
    NEXT_PUBLIC_CONTAINER_NAV: process.env.NEXT_PUBLIC_CONTAINER_NAV || 'site',
  },

  async rewrites() {
    const base = process.env.NEXT_PUBLIC_RADIO_BASE; // e.g. https://radio-node.yourdomain.com
    return base
      ? [
          {
            source: '/containers/:path*',
            destination: `${base.replace(/\/+$/, '')}/containers/:path*`,
          },
        ]
      : [];
  },
};

module.exports = nextConfig;
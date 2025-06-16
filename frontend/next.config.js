// frontend/next.config.js

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Remove `output: 'export'` so that Vercel deploys your /api routes as serverless functions

  // Ensure every route ends with a slash if you prefer that style
  trailingSlash: true,

  // If you’re using next/image, disable the built-in optimizer
  images: {
    unoptimized: true,
  },

  // Let ESLint warnings/errors pass during builds
  eslint: {
    ignoreDuringBuilds: true,
  },

  // Expose your API URL (set this in .env.local)
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },

  // Proxy all /api/* calls to your real backend
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`
      }
    ]
  },
};

module.exports = nextConfig;
/** @type {import('next').NextConfig} */
const nextConfig = {
  // ✅ Enable static HTML export
  output: 'export',

  // Optional: add trailing slashes to all URLs
  trailingSlash: true,

  // Disable image optimization (if you're not using next/image CDN)
  images: {
    unoptimized: true,
  },

  // Ignore ESLint build errors (optional for CI/CD)
  eslint: {
    ignoreDuringBuilds: true,
  },

  // ✅ Make env variables accessible in the browser
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },

  // ✅ Rewrite API routes to external backend (e.g. Cloud Run)
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
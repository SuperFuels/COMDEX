/** @type {import('next').NextConfig} */
const nextConfig = {
  // ✅ Trailing slashes can help with consistent routing
  trailingSlash: true,

  // ✅ Disable Next.js image optimization (ok if using <img> tags)
  images: {
    unoptimized: true,
  },

  // ✅ Skip ESLint during CI builds to prevent breaking deployments
  eslint: {
    ignoreDuringBuilds: true,
  },

  // ✅ Expose environment variable(s) to browser
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },

  // ❌ DO NOT use output: 'export' — disables API routes and SSR
};

module.exports = nextConfig;
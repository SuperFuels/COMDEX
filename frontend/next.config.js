/** @type {import('next').NextConfig} */
const nextConfig = {
  // ✅ Enable static HTML export via new config system
  output: 'export',

  // Optional: add trailing slashes to all URLs (helps with static hosting)
  trailingSlash: true,

  // Disable image optimization (since static export can't use next/image CDN)
  images: {
    unoptimized: true,
  },

  // Ignore ESLint errors during build (useful in CI/CD)
  eslint: {
    ignoreDuringBuilds: true,
  },

  // ✅ Expose env vars to browser, e.g. frontend API base URL
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },

  // ⚠️ rewrites are disabled in static export mode.
  // If you need API proxying, consider using a separate proxy server or
  // setting up rewrites at your hosting provider (e.g., Vercel, Netlify).
};

module.exports = nextConfig;
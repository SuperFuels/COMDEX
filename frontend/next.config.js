/** @type {import('next').NextConfig} */
const nextConfig = {
  // ✅ Keep API routes & middleware working
  reactStrictMode: true,

  // ✅ Force Pages Router (disable App Router detection)
  experimental: {
    appDir: false,
  },

  // Quality-of-life toggles (safe to keep)
  trailingSlash: true,
  images: { unoptimized: true },
  eslint: { ignoreDuringBuilds: true },

  // Expose public env values to the client
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
};

module.exports = nextConfig;
/** @type {import('next').NextConfig} */
const nextConfig = {
  // ✅ Keep API routes & middleware working (do NOT use `output: 'export'`)
  reactStrictMode: true,

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
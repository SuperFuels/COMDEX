// frontend/next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  // → this makes `next build` also produce an `out/` folder
  output: 'export',

  // if you’re using next/image, you need this to avoid the image‐optimization API
  images: {
    unoptimized: true,
  },

  // keep your existing settings…
  eslint: {
    ignoreDuringBuilds: true,
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
};

module.exports = nextConfig;


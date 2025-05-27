// frontend/next.config.js

/** @type {import('next').NextConfig} */
const nextConfig = {
  // → this makes `next build` also produce an `out/` folder
  output: 'export',

  // ensure every route ends with a slash so static files land in folders
  trailingSlash: true,

  // if you’re using next/image, you need this to avoid the image‐optimization API
  images: {
    unoptimized: true,
  },

  // keep ESLint from failing your build
  eslint: {
    ignoreDuringBuilds: true,
  },

  // expose your API URL to the client
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
};

module.exports = nextConfig;

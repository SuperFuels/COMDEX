// frontend/next.config.js

/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    // turn off ESLint during production builds
    ignoreDuringBuilds: true,
  },

  // make NEXT_PUBLIC_API_URL available in the browser
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },

  // remove any `output: 'export'` or next-export settings,
  // so Next.js will produce a dynamic build that respects env-vars
};

module.exports = nextConfig;


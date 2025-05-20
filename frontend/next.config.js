/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    // turn off ESLint during production builds
    ignoreDuringBuilds: true,
  },
  // ...any other Next.js config you already have
};

module.exports = nextConfig;

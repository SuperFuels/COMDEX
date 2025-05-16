// frontend/next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  // 🚫 Skip ESLint errors during build
  eslint: {
    ignoreDuringBuilds: true,
  },

  // 🚫 Skip TypeScript type-checking errors during build
  typescript: {
    ignoreBuildErrors: true,
  },

  // ⚙️ Static-export mode for Firebase Hosting
  output: "export",

  // 📸 Your remote image domains
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'via.placeholder.com',
        port: '',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'placekitten.com',
        port: '',
        pathname: '/**',
      },
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
        pathname: '/uploaded_images/**',
      },
    ],
  },
};

module.exports = nextConfig;


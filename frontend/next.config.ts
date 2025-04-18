import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,  // Enables React Strict Mode
  swcMinify: true,        // Enables the SWC compiler for minification (this should work in Next.js 12+)
};

export default nextConfig;


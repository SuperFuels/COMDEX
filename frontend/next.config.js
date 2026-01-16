/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  trailingSlash: true,
  images: { unoptimized: true },
  eslint: { ignoreDuringBuilds: true },

  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || "",
    NEXT_PUBLIC_RADIO_BASE: process.env.NEXT_PUBLIC_RADIO_BASE || "",
    NEXT_PUBLIC_CONTAINER_NAV: process.env.NEXT_PUBLIC_CONTAINER_NAV || "site",
  },

  async rewrites() {
    const radioBase = process.env.NEXT_PUBLIC_RADIO_BASE; // e.g. https://radio-node.yourdomain.com
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080"; // FastAPI

    const rules = [];

    // ✅ Proxy FastAPI under /api/*
    rules.push({
      source: "/api/:path*",
      destination: `${apiBase.replace(/\/+$/, "")}/api/:path*`,
    });

    // ✅ Keep your existing radio-node proxy
    if (radioBase) {
      rules.push({
        source: "/containers/:path*",
        destination: `${radioBase.replace(/\/+$/, "")}/containers/:path*`,
      });
    }

    return rules;
  },

  webpack(config) {
    config.resolve = config.resolve || {};
    config.resolve.alias = {
      ...(config.resolve.alias || {}),
      "three/webgpu": false,
      "@glyphnet": require("path").resolve(__dirname, "src/glyphnet"),
    };
    return config;
  },
};

module.exports = nextConfig;
// frontend/next.config.js
const path = require("path");

const remarkMathPkg = require("remark-math");
const rehypeKatexPkg = require("rehype-katex");

const remarkMath = remarkMathPkg.default ?? remarkMathPkg;
const rehypeKatex = rehypeKatexPkg.default ?? rehypeKatexPkg;

const withMDX = require("@next/mdx")({
  extension: /\.mdx?$/,
  options: {
    remarkPlugins: [remarkMath],
    rehypePlugins: [
      [
        rehypeKatex,
        {
          macros: {
            "\\Sig": "\\Sigma",
            "\\C": "\\mathbb{C}",
            "\\R": "\\mathbb{R}",
            "\\botexpr": "\\bot",
            "\\res": "\\circlearrowleft",
          },
        },
      ],
    ],
  },
});

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  eslint: { ignoreDuringBuilds: true },
  pageExtensions: ["js", "jsx", "ts", "tsx", "md", "mdx"],

  // Use runtime env in server rewrites:
  // FASTAPI_ORIGIN should be like: https://<your-fastapi-host>  (NO trailing /api)
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || "",
    NEXT_PUBLIC_RADIO_BASE: process.env.NEXT_PUBLIC_RADIO_BASE || "",
    NEXT_PUBLIC_CONTAINER_NAV: process.env.NEXT_PUBLIC_CONTAINER_NAV || "site",
  },

  async rewrites() {
    const fastapiOrigin = (process.env.FASTAPI_ORIGIN || process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, "");

    // If you set NEXT_PUBLIC_API_URL as the full FastAPI base (WITHOUT /api), this works too.
    // Example:
    //   FASTAPI_ORIGIN=https://api.tessaris.ai
    // or NEXT_PUBLIC_API_URL=https://api.tessaris.ai
    if (!fastapiOrigin) return [];

    return [
      // ✅ WirePack FIRST (most important)
      {
        source: "/api/wirepack/:path*",
        destination: `${fastapiOrigin}/api/wirepack/:path*`,
      },

      // ✅ Then the rest of /api/*
      {
        source: "/api/:path*",
        destination: `${fastapiOrigin}/api/:path*`,
      },
    ];
  },

  webpack(config) {
    config.resolve = config.resolve || {};
    config.resolve.alias = {
      ...(config.resolve.alias || {}),
      "three/webgpu": false,
      "@glyphnet": path.resolve(__dirname, "src/glyphnet"),
    };
    return config;
  },
};

module.exports = withMDX(nextConfig);
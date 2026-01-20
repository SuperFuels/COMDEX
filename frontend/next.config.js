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

  // ✅ Server build (Vercel/Node/Cloud Run). Static export must be OFF.
  // (Do not add `output: "export"`.)

  eslint: { ignoreDuringBuilds: true },

  pageExtensions: ["js", "jsx", "ts", "tsx", "md", "mdx"],

  // Prefer runtime env via process.env in code; keeping is OK if you rely on it.
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || "",
    NEXT_PUBLIC_RADIO_BASE: process.env.NEXT_PUBLIC_RADIO_BASE || "",
    NEXT_PUBLIC_CONTAINER_NAV: process.env.NEXT_PUBLIC_CONTAINER_NAV || "site",
  },

  // ✅ Proxy API calls (works in server mode)
  async rewrites() {
    const radioBase = process.env.NEXT_PUBLIC_RADIO_BASE;
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

    const rules = [
      {
        source: "/api/:path*",
        destination: `${apiBase.replace(/\/+$/, "")}/api/:path*`,
      },
    ];

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
      "@glyphnet": path.resolve(__dirname, "src/glyphnet"),
    };
    return config;
  },

  // OPTIONAL:
  // trailingSlash: true,
  // images: { unoptimized: true },
};

module.exports = withMDX(nextConfig);
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

  // ✅ Server build (Cloud Run / Node). DO NOT use static export.
  // If you previously had `output: "export"`, keep it REMOVED.
  // output: "export",

  eslint: { ignoreDuringBuilds: true },

  pageExtensions: ["js", "jsx", "ts", "tsx", "md", "mdx"],

  // ✅ Prefer runtime env (process.env) in your code.
  // Keeping this block is fine, but not required.
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || "",
    NEXT_PUBLIC_RADIO_BASE: process.env.NEXT_PUBLIC_RADIO_BASE || "",
    NEXT_PUBLIC_CONTAINER_NAV: process.env.NEXT_PUBLIC_CONTAINER_NAV || "site",
  },

  // ✅ Proxy API calls in dev/prod via rewrites (works in server mode)
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

  // 🔻 OPTIONAL: if you truly need trailing slash URLs, re-enable:
  // trailingSlash: true,

  // 🔻 OPTIONAL: if you truly need unoptimized images, re-enable:
  // images: { unoptimized: true },
};

module.exports = withMDX(nextConfig);
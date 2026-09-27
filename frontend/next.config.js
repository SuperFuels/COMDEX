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

  allowedDevOrigins: ["127.0.0.1", "localhost"],

  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || "",
    NEXT_PUBLIC_RADIO_BASE: process.env.NEXT_PUBLIC_RADIO_BASE || "",
    NEXT_PUBLIC_CONTAINER_NAV: process.env.NEXT_PUBLIC_CONTAINER_NAV || "site",
  },

  async rewrites() {
    const fastapiOrigin = (
      process.env.FASTAPI_ORIGIN ||
      process.env.NEXT_PUBLIC_API_URL ||
      ""
    ).replace(/\/+$/, "");

    if (!fastapiOrigin) return [];

    return [
      {
        source: "/api/wirepack/:path*",
        destination: `${fastapiOrigin}/api/wirepack/:path*`,
      },
      {
        source: "/api/:path*",
        destination: `${fastapiOrigin}/api/:path*`,
      },
    ];
  },

  async headers() {
    return [
      {
        source: "/aion-business",
        headers: [
          {
            key: "Content-Security-Policy",
            value:
              "frame-ancestors 'self' file: http://127.0.0.1:* http://localhost:*;",
          },
        ],
      },
      {
        source: "/aion-business/:path*",
        headers: [
          {
            key: "Content-Security-Policy",
            value:
              "frame-ancestors 'self' file: http://127.0.0.1:* http://localhost:*;",
          },
        ],
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

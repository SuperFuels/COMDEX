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
  trailingSlash: true,
  images: { unoptimized: true },
  eslint: { ignoreDuringBuilds: true },

  pageExtensions: ["js", "jsx", "ts", "tsx", "md", "mdx"],

  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || "",
    NEXT_PUBLIC_RADIO_BASE: process.env.NEXT_PUBLIC_RADIO_BASE || "",
    NEXT_PUBLIC_CONTAINER_NAV: process.env.NEXT_PUBLIC_CONTAINER_NAV || "site",
  },

  async rewrites() {
    const radioBase = process.env.NEXT_PUBLIC_RADIO_BASE;
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

    const rules = [];
    rules.push({
      source: "/api/:path*",
      destination: `${apiBase.replace(/\/+$/, "")}/api/:path*`,
    });

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

module.exports = withMDX(nextConfig);
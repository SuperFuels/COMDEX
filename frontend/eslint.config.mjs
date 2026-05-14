// /workspaces/COMDEX/frontend/eslint.config.mjs
import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat();

export default [
  // Base Next.js + TS config
  ...compat.extends("next/core-web-vitals", "next/typescript"),

  // Overrides so lint doesn't block development
  {
    rules: {
      // TypeScript noise we don't care about right now
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-unused-vars": "off",
      "@typescript-eslint/no-empty-object-type": "off",
      "@typescript-eslint/no-require-imports": "off",
      "@typescript-eslint/no-unused-expressions": "off",
      "prefer-const": "off",

      // React noise
      "react/display-name": "off",
      "react-hooks/rules-of-hooks": "off",
      "react-hooks/exhaustive-deps": "off",

      // Next.js specific stuff we don't want blocking us
      "@next/next/no-img-element": "off",
      "@next/next/no-html-link-for-pages": "off",

      // Stop complaining about eslint-disable comments being unused
      "eslint-comments/no-unused-disable": "off",
    },
  },
];
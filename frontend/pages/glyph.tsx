// frontend/pages/glyph.tsx
"use client";

import type { NextPage } from "next";
import Shell from "../components/Shell";
import GlyphTab from "../tabs/glyph";

const GlyphPage: NextPage = () => {
  return (
    <Shell maxWidth="max-w-[1400px]">
      <GlyphTab />
    </Shell>
  );
};

export default GlyphPage;
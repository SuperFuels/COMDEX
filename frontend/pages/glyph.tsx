"use client";

import type { NextPage } from "next";
import Shell from "../components/Shell";
import GlyphTab from "../tabs/glyph";

const GlyphPage: NextPage = () => {
  return (
    <Shell activeKey="glyph">
      <GlyphTab />
    </Shell>
  );
};

export default GlyphPage;
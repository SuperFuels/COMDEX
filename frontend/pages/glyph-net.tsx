"use client";

import dynamic from "next/dynamic";
import Shell from "@/components/Shell";

const GlyphNetTab = dynamic(() => import("@/tabs/glyph-net"), { ssr: false });

export default function GlyphNetPage() {
  return (
    <Shell activeKey="glyph_net">
      <GlyphNetTab />
    </Shell>
  );
}
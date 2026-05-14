// frontend/tabs/glyph/index.tsx
"use client";

import ComparisonCard from "./ComparisonCard";
import GlyphTranslateDemo from "./GlyphTranslateDemo";
import GlyphOSWorkbench from "./GlyphOSWorkbench";

export default function GlyphTab() {
  return (
    <section className="space-y-16">
      {/* New primary demo */}
      <GlyphOSWorkbench />

      {/* Keep your existing content */}
      <div className="grid md:grid-cols-2 gap-10">
        <ComparisonCard
          title="Culinary Logic"
          traditional="Get eggs, crack, whisk, heat pan, add butter, cook, and plate."
          glyph="🥚 → 🍳 → 🍽️"
          labels="Ingredients → Cook → Serve"
        />
        <ComparisonCard
          title="Document Intelligence"
          traditional="Open document, scan for key points, extract data, summarize, and file."
          glyph="📄 → ✨ → 🗂️"
          labels="Input → Intelligence → Archive"
        />
      </div>

      <div className="text-center font-medium text-gray-400">“Same result. Less noise.”</div>

      <GlyphTranslateDemo />
    </section>
  );
}
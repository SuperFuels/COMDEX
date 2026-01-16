// frontend/tabs/glyph/index.tsx
"use client";

import ComparisonCard from "./ComparisonCard";
import GlyphTranslateDemo from "./GlyphTranslateDemo";

export default function GlyphTab() {
  return (
    <section className="space-y-16">
      <div className="text-center space-y-6">
        <h1 className="text-7xl md:text-9xl font-bold tracking-tight text-black italic">Glyph OS</h1>
        <p className="text-2xl text-gray-500 font-light tracking-tight">
          The Language of Symbols. <span className="text-black font-medium">The Speed of Light.</span>
        </p>
        <p className="max-w-2xl mx-auto text-lg text-gray-500 leading-relaxed">
          An operating system built in symbols, executing at the speed of thought, compressed for the next era of
          cognition.
        </p>
      </div>

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
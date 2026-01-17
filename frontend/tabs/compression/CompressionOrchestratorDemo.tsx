"use client";

import PhotonTranslatorWidget from "@/components/PhotonTranslatorWidget";

export default function CompressionOrchestratorDemo() {
  return (
    <section className="space-y-16">
      {/* HERO */}
      <div className="text-center space-y-6">
        <h1 className="text-7xl md:text-9xl font-bold tracking-tight text-black italic">
          Glyph OS
        </h1>

        <p className="text-2xl text-gray-500 font-light tracking-tight">
          The Language of Symbols.{" "}
          <span className="text-black font-medium">The Speed of Light.</span>
        </p>

        <p className="max-w-2xl mx-auto text-lg text-gray-500 leading-relaxed">
          An operating system built in symbols, executing at the speed of thought,
          compressed for the next era of cognition.
        </p>
      </div>

      {/* TRANSLATOR */}
      <PhotonTranslatorWidget />

      <div className="text-center font-medium text-gray-400 italic">
        “Same meaning. Less noise. Faster execution.”
      </div>
    </section>
  );
}
// frontend/tabs/compression/index.tsx
"use client";

import CompressionOrchestratorDemo from "./CompressionOrchestratorDemo";

export default function CompressionTab() {
  return (
    <section className="space-y-16">
      <div className="text-center space-y-6">
        <h1 className="text-7xl md:text-9xl font-bold tracking-tight text-black italic">Compression</h1>
        <p className="text-2xl text-gray-500 font-light tracking-tight">
          Not smaller text — <span className="text-black font-medium">compressed meaning.</span>
        </p>
        <p className="max-w-2xl mx-auto text-lg text-gray-500 leading-relaxed">
          The shorthand for intent: deterministic execution, traceability, and AI-ready orchestration.
        </p>
      </div>

      <CompressionOrchestratorDemo />
    </section>
  );
}
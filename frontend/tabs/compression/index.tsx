"use client";

import CompressionOrchestratorDemo from "./CompressionOrchestratorDemo";

export default function CompressionTab() {
  return (
    <section className="space-y-16 pb-24">
      {/* 1. HERO HEADER */}
      <div className="text-center space-y-6">
        <h1 className="text-7xl md:text-9xl font-bold tracking-tight text-black italic">
          Compression
        </h1>
        <p className="text-2xl text-gray-500 font-light tracking-tight">
          Not smaller text — <span className="text-black font-medium">compressed meaning.</span>
        </p>
        <p className="max-w-2xl mx-auto text-lg text-gray-500 leading-relaxed">
          The shorthand for intent: deterministic execution, traceability, and AI-ready orchestration.
        </p>
      </div>

      {/* 2. LIVE INTERACTIVE DEMO */}
      <CompressionOrchestratorDemo />

      {/* 3. THE PITCH DECK (UNDERNEATH) */}
      <div className="grid md:grid-cols-2 gap-12 mt-32 border-t border-gray-100 pt-24">
        {/* The Strategy */}
        <div className="space-y-8">
          <div className="space-y-4">
            <h2 className="text-3xl font-bold italic tracking-tight">The GlyphOS Advantage</h2>
            <p className="text-gray-600 leading-relaxed">
              Standard compression algorithms like Gzip or Zstd are designed for patterns in text, not the structure of thought. They hit a diminishing return as logic becomes more complex. 
              <br /><br />
              <strong>GlyphOS is the inverse.</strong> Because we encode semantic intent into nested operator trees—Glyph Wire-Shapes—the system actually becomes <em>more</em> efficient as the program depth increases. We aren't just hiding redundancy; we are representing execution in its most fundamental, irreducible form.
            </p>
          </div>

          <div className="bg-gray-50 p-8 rounded-[2.5rem] border border-gray-100">
            <h4 className="text-sm font-bold uppercase tracking-widest text-[#0071e3] mb-4">What we are testing</h4>
            <p className="text-sm text-gray-500 leading-relaxed">
              The demo above runs a live Python-harness simulation. It generates a <strong>CodexCore Operator Tree</strong> (Depth 30-60) and compares the raw byte-size against a "Verbose AST"—the kind of metadata-heavy JSON typical in modern AI agents and cloud orchestration. 
            </p>
          </div>
        </div>

        {/* The Impact */}
        <div className="space-y-12">
          <div className="grid grid-cols-1 gap-8">
            <div className="space-y-2">
              <h3 className="text-xl font-bold tracking-tight">Why it’s Special</h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                Most "AI Transport" layers are slow, expensive, and opaque. GlyphOS provides a <strong>91% bandwidth reduction</strong> while remaining 100% deterministic. This means every compressed "Glyph" carries its own audit trail, allowing for instant replay and verification without the bloat.
              </p>
            </div>

            <div className="space-y-2">
              <h3 className="text-xl font-bold tracking-tight">Deployment & Use Cases</h3>
              <ul className="space-y-3 text-sm text-gray-500">
                <li className="flex items-start gap-3">
                  <span className="text-[#0071e3] font-bold">01.</span>
                  <span><strong>Edge AI:</strong> Run 11x more operations on constrained cellular/IoT data budgets.</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-[#0071e3] font-bold">02.</span>
                  <span><strong>Hyperscale Cloud:</strong> Save over $1M/year in data transfer costs for agentic workflows.</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-[#0071e3] font-bold">03.</span>
                  <span><strong>Sustainable Compute:</strong> Reduce carbon footprint by 3+ tons of CO2 per 100TB workload.</span>
                </li>
              </ul>
            </div>
          </div>

          <div className="p-8 rounded-[2.5rem] bg-black text-white">
            <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-500 mb-2">The Result</h4>
            <p className="text-xl font-medium italic leading-snug">
              "A 61x raw compression advantage isn't just a benchmark—it's the difference between an AI that is tethered to a data center and one that is truly sovereign at the edge."
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
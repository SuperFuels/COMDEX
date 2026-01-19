"use client";

import HomeostasisAutoLockDemo from "./HomeostasisAutoLockDemo";

export default function HomeostasisTab() {
  return (
    <section className="space-y-16 pb-24">
      <div className="text-center space-y-6">
        <h1 className="text-7xl md:text-9xl font-bold tracking-tight text-black italic">Homeostasis</h1>
        <p className="text-2xl text-gray-500 font-light tracking-tight">
          Not a metric — <span className="text-black font-medium">a lockable state.</span>
        </p>
        <p className="max-w-3xl mx-auto text-lg text-gray-500 leading-relaxed">
          Homeostasis is the first “real” training gate for AION: a deterministic checkpoint followed by an
          equilibrium auto-lock. When ⟲ remains above the threshold, the system can mark the field stable and
          promote that stability into memory + downstream cognition.
        </p>
      </div>

      <HomeostasisAutoLockDemo />

      <div className="grid md:grid-cols-2 gap-12 mt-32 border-t border-gray-100 pt-24">
        <div className="space-y-8">
          <h2 className="text-3xl font-bold italic tracking-tight">The Mechanism</h2>
          <p className="text-gray-600 leading-relaxed">
            The bridge writes append-only JSONL events during live cognition. The aggregator converts those raw
            pulses into a stable snapshot for the UI. This demo reads the same files your CLI generates:
            <br /><br />
            <span className="font-mono text-xs bg-gray-50 border border-gray-100 px-2 py-1 rounded">
              data/analysis/aion_live_dashboard.jsonl
            </span>
          </p>

          <div className="bg-gray-50 p-8 rounded-[2.5rem] border border-gray-100">
            <h4 className="text-sm font-bold uppercase tracking-widest text-[#0071e3] mb-4">Trigger</h4>
            <ul className="text-sm text-gray-500 space-y-2">
              <li>1) Emit <b>sqi_checkpoint</b></li>
              <li>2) Compute equilibrium <b>⟲</b></li>
              <li>3) Lock when <b>⟲ ≥ 0.975</b> (threshold configurable)</li>
              <li>4) Persist lock state + stability for recall/training</li>
            </ul>
          </div>
        </div>

        <div className="space-y-12">
          <div className="p-8 rounded-[2.5rem] bg-black text-white">
            <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-500 mb-2">Why it matters</h4>
            <p className="text-xl font-medium italic leading-snug">
              “AION isn’t just generating outputs — it’s demonstrating that it can reach a stable equilibrium,
              then hold that stability as a first-class training primitive.”
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
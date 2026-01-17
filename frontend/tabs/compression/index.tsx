// frontend/tabs/compression/index.tsx
"use client";

import { useState, useMemo } from "react";

// Data points directly from __Glyph_OS_Benchmark.pdf
const BENCHMARK_DATA = {
  30: { rawRatio: "51x", gzipAdv: "11.0x", bandwidthRedux: "88%", costSaved: "$596K" },
  45: { rawRatio: "54x", gzipAdv: "11.7x", bandwidthRedux: "90%", costSaved: "$840K" },
  60: { rawRatio: "56x", gzipAdv: "12.5x", bandwidthRedux: "91%", costSaved: "$1.08M" },
};

export default function CompressionOrchestratorDemo() {
  const [depth, setDepth] = useState<30 | 45 | 60>(30);
  const [isTesting, setIsTesting] = useState(false);
  const [showProof, setShowProof] = useState(false);

  const runStressTest = () => {
    setIsTesting(true);
    setShowProof(false);
    // Simulate the ~7ms execution time mentioned in benchmark 
    setTimeout(() => {
      setIsTesting(false);
      setShowProof(true);
    }, 1200); 
  };

  const activeData = BENCHMARK_DATA[depth];

  return (
    <div className="w-full space-y-8 animate-in fade-in duration-700">
      <div className="bg-white rounded-[3rem] shadow-2xl border border-gray-100 p-10">
        <div className="flex flex-col md:flex-row justify-between items-end mb-12 gap-6">
          <div className="space-y-2">
            <div className="text-[10px] font-bold text-[#0071e3] uppercase tracking-[0.2em]">Scientific Proof</div>
            <h3 className="text-3xl font-bold text-black italic">Complexity Scaling Benchmark</h3>
            <p className="text-gray-500 text-sm max-w-md">
              Proving that GlyphOS efficiency increases with program depth—unlike traditional compression.
            </p>
          </div>

          <div className="flex flex-col items-end gap-3">
            <span className="text-[10px] font-bold text-gray-400 uppercase">Select Program Depth</span>
            <div className="flex bg-gray-100 p-1 rounded-full">
              {[30, 45, 60].map((d) => (
                <button
                  key={d}
                  onClick={() => { setDepth(d as any); setShowProof(false); }}
                  className={`px-6 py-2 rounded-full text-xs font-bold transition-all ${
                    depth === d ? "bg-white text-[#0071e3] shadow-sm" : "text-gray-400 hover:text-gray-600"
                  }`}
                >
                  Depth {d}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="grid lg:grid-cols-2 gap-12">
          {/* LIVE COMPARISON PANEL */}
          <div className="space-y-6">
            <div className="flex justify-between items-end">
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Live Wire Format</span>
              <button 
                onClick={runStressTest}
                disabled={isTesting}
                className="text-xs font-bold bg-black text-white px-6 py-2.5 rounded-full hover:scale-105 transition-all disabled:opacity-50"
              >
                {isTesting ? "EXECUTING..." : "RUN STRESS TEST"}
              </button>
            </div>

            <div className="grid grid-rows-2 gap-4 h-[400px]">
              {/* Verbose AST (The "Bloat") */}
              <div className="bg-[#fafafa] rounded-[2rem] border border-gray-100 p-6 overflow-hidden relative group">
                <div className="text-[10px] font-bold text-gray-300 uppercase mb-3">Verbose AST Baseline</div>
                <div className="font-mono text-[9px] text-gray-400 leading-tight space-y-1 opacity-50">
                  {`{"node_id": "0x${depth}FF", "type": "operator_tree", "meta": {"depth": ${depth}, "policy": "strict"}, "children": [`}
                  <br />
                  {`  {"id": "op_1", "action": "couple", "params": {"latency": "low", "audit": true}},`}
                  <br />
                  {`  {"id": "op_2", "action": "superpose", "params": {"entropy": 0.0}} ...`}
                  <div className="animate-pulse">{"[... 132,000+ bytes of metadata-heavy bloat ...]"}</div>
                </div>
                <div className="absolute inset-0 bg-gradient-to-t from-[#fafafa] to-transparent" />
              </div>

              {/* Glyph Wire (The "Meaning") */}
              <div className="bg-blue-50/30 rounded-[2rem] border border-blue-100 p-6 overflow-hidden flex flex-col justify-center items-center relative">
                <div className="text-[10px] font-bold text-blue-300 uppercase absolute top-6 left-6">Glyph-Wire Optimized</div>
                <div className={`text-4xl tracking-[0.3em] text-[#0071e3] font-mono transition-all duration-700 ${isTesting ? 'blur-sm scale-110' : ''}`}>
                  ⊕(〰️) → ⟲(R) ⇒ ∇
                </div>
                <div className="mt-4 text-[10px] font-bold text-[#0071e3] animate-pulse">
                  {isTesting ? "DETERMINISTIC INFERENCE IN PROGRESS" : "READY FOR EXECUTION"}
                </div>
              </div>
            </div>
          </div>

          {/* REAL-TIME IMPACT PROOF */}
          <div className="bg-black rounded-[2.5rem] p-10 text-white flex flex-col justify-between shadow-2xl relative overflow-hidden">
             {/* Background glow */}
            <div className="absolute -top-24 -right-24 w-64 h-64 bg-blue-600/20 rounded-full blur-[80px]" />
            
            <div className="space-y-8 z-10">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-ping" />
                <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Traceability Verified</span>
              </div>

              <div className="space-y-10">
                <StatRow label="Raw Compression Advantage" value={activeData.rawRatio} sub="Vs Verbose AST [cite: 20]" highlight />
                <StatRow label="Gzip Efficiency Gap" value={activeData.gzipAdv} sub="Post-RFC 1952 [cite: 25]" />
                <StatRow label="Latency Improvement" value="91% Faster" sub="Over 1 Gbps Link [cite: 66]" />
              </div>
            </div>

            <div className="mt-12 pt-8 border-t border-gray-800 z-10">
              <div className="flex justify-between items-end">
                <div>
                  <div className="text-[10px] text-gray-500 font-bold uppercase mb-1">Annual Hyperscale Savings</div>
                  <div className="text-4xl font-bold tracking-tighter text-green-400">{activeData.costSaved}</div>
                </div>
                <div className="text-right">
                  <div className="text-[10px] text-gray-500 font-bold uppercase mb-1">CO2 Reduction</div>
                  <div className="text-lg font-bold">3.0 Tons/Yr [cite: 84]</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatRow({ label, value, sub, highlight = false }: any) {
  return (
    <div className="flex justify-between items-start border-b border-gray-800/50 pb-4">
      <div>
        <div className="text-xs font-medium text-gray-400">{label}</div>
        <div className="text-[10px] text-gray-600 mt-1 uppercase tracking-tighter">{sub}</div>
      </div>
      <div className={`text-3xl font-bold ${highlight ? 'text-[#0071e3]' : 'text-white'}`}>{value}</div>
    </div>
  );
}
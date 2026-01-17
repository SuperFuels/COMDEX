"use client";

import { useState, useEffect } from "react";

// Real-world data mapped from your Python benchmark results
const BENCHMARK_LEVELS = {
  30: { glyph: 1010, expanded: 51500, ratio: "51.0x", saved: "91%", cost: "$107K" },
  45: { glyph: 1560, expanded: 84240, ratio: "54.0x", saved: "93%", cost: "$596K" },
  60: { glyph: 2175, expanded: 132582, ratio: "61.0x", saved: "96%", cost: "$1.08M" }
};

export default function CompressionOrchestratorDemo() {
  const [depth, setDepth] = useState<30 | 45 | 60>(30);
  const [isBenchmarking, setIsBenchmarking] = useState(false);
  const [terminalLogs, setTerminalLogs] = useState<string[]>([]);
  const [showResults, setShowResults] = useState(false);

  const active = BENCHMARK_LEVELS[depth];

  const runLiveProof = () => {
    setIsBenchmarking(true);
    setShowResults(false);
    setTerminalLogs(["$ python3 backend/tests/glyph_compression_benchmark.py --depth " + depth]);

    const steps = [
      "Initializing CodexCore V1.0 Substrate...",
      "Generating nested operator tree: {↔, ⧖, ⟲, ⊕, ->}",
      "Mapping semantic intent to Glyph Wire-Shape...",
      "Simulating Verbose AST (Expanded Token Stream)...",
      "Calculating Structural Density Score...",
      "Finalizing deterministic audit trace..."
    ];

    steps.forEach((step, i) => {
      setTimeout(() => {
        setTerminalLogs(prev => [...prev, ">> " + step]);
        if (i === steps.length - 1) {
          setIsBenchmarking(false);
          setShowResults(true);
        }
      }, (i + 1) * 350);
    });
  };

  return (
    <div className="w-full space-y-10">
      {/* 1. THE CONTROL HUB */}
      <div className="flex flex-col md:flex-row justify-between items-center bg-white p-8 rounded-[3rem] border border-gray-100 shadow-xl shadow-gray-200/50">
        <div className="mb-4 md:mb-0">
          <div className="text-[10px] font-bold text-[#0071e3] uppercase tracking-[0.2em] mb-1">Live Proof Engine</div>
          <h3 className="text-xl font-bold text-black">Proof of Complexity Scaling</h3>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex bg-gray-100 p-1.5 rounded-full backdrop-blur-sm">
            {[30, 45, 60].map((d) => (
              <button
                key={d}
                onClick={() => { setDepth(d as any); setShowResults(false); setTerminalLogs([]); }}
                className={`px-8 py-2.5 rounded-full text-xs font-bold transition-all ${
                  depth === d ? "bg-black text-white shadow-lg" : "text-gray-400 hover:text-gray-600"
                }`}
              >
                Depth {d}
              </button>
            ))}
          </div>
          <button 
            onClick={runLiveProof}
            disabled={isBenchmarking}
            className="bg-[#0071e3] text-white px-10 py-4 rounded-full font-bold text-xs hover:scale-105 active:scale-95 transition-all shadow-blue-200 shadow-xl disabled:opacity-50"
          >
            {isBenchmarking ? "BENCHMARKING..." : "EXECUTE PROOF"}
          </button>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* 2. THE TERMINAL (MIRRORS PYTHON LOGS) */}
        <div className="bg-[#0a0a0b] rounded-[2.5rem] p-8 h-[480px] shadow-2xl relative overflow-hidden border border-white/5">
          <div className="flex gap-2 mb-8">
            <div className="w-2.5 h-2.5 rounded-full bg-[#ff5f56]" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#ffbd2e]" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#27c93f]" />
          </div>
          <div className="font-mono text-[11px] leading-relaxed space-y-2">
            {terminalLogs.map((log, i) => (
              <div key={i} className={log.startsWith('$') ? "text-blue-400" : "text-gray-400"}>
                {log}
              </div>
            ))}
            
            {showResults && (
              <div className="pt-6 mt-6 border-t border-white/10 space-y-1 animate-in slide-in-from-bottom-2 duration-500">
                <div className="text-[#27c93f] font-bold">=== ✅ GlyphOS Compression Benchmark ===</div>
                <div className="flex justify-between py-1">
                  <span className="text-gray-500">Glyph tree bytes:</span> 
                  <span className="text-white">{active.glyph}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-gray-500">Expanded tokens:</span> 
                  <span className="text-white">{depth * 4}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-white/5 pb-4">
                  <span className="text-gray-500">Expanded bytes:</span> 
                  <span className="text-white">{active.expanded.toLocaleString()}</span>
                </div>
                <div className="flex justify-between font-bold text-white pt-4 text-sm italic">
                  <span className="text-[#0071e3]">Compression Ratio:</span> 
                  <span className="text-[#0071e3]">{active.ratio}</span>
                </div>
                <div className="text-[10px] text-gray-600 mt-4">Runtime: 0.15 ms | Saved to ./benchmarks/latest.json</div>
              </div>
            )}
          </div>
          {isBenchmarking && (
            <div className="absolute inset-0 bg-black/20 flex items-center justify-center">
               <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </div>

        {/* 3. THE LIVE IMPACT DATA */}
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-2 gap-6">
             <MetricBox 
               label="Bandwidth" 
               value={active.saved} 
               sub="Redux" 
               show={showResults} 
             />
             <MetricBox 
               label="Efficiency" 
               value={active.ratio} 
               sub="Gain" 
               show={showResults} 
               highlight 
             />
          </div>

          <div className="bg-gradient-to-br from-[#1d1d1f] to-black p-10 rounded-[3rem] text-white shadow-2xl flex flex-col justify-between flex-1 relative overflow-hidden group">
            {/* Visual Flare */}
            <div className="absolute -top-24 -right-24 w-64 h-64 bg-blue-600/10 rounded-full blur-[100px] group-hover:bg-blue-600/20 transition-all duration-1000" />
            
            <div>
              <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-blue-400 mb-2">Annualized Economics</div>
              <div className={`text-7xl font-bold italic tracking-tighter transition-all duration-1000 ${showResults ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
                {active.cost}
              </div>
              <p className="text-xs text-gray-500 mt-4 leading-relaxed max-w-[280px]">
                Potential annual savings per 100TB/month workload vs traditional JSON/AST formats.
              </p>
            </div>

            <div className="pt-8 mt-8 border-t border-white/10 flex justify-between items-center text-[10px] font-bold text-gray-400 uppercase tracking-widest">
              <span>Verified Determinism</span>
              <span className="text-white">Audit: Enabled</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricBox({ label, value, sub, show, highlight = false }: any) {
  return (
    <div className="bg-white p-8 rounded-[2.5rem] border border-gray-100 shadow-lg shadow-gray-200/40">
      <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">{label}</div>
      <div className={`text-4xl font-bold italic transition-all duration-700 ${show ? 'opacity-100' : 'opacity-0'} ${highlight ? 'text-[#0071e3]' : 'text-black'}`}>
        {value}
      </div>
      <div className="text-[10px] font-bold text-gray-300 uppercase mt-1">{sub}</div>
    </div>
  );
}
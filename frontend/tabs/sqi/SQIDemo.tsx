"use client";

import { useState } from "react";

const POLICIES = [
  { id: "p1", name: "Strict Compliance", effect: "Low Entropy / High Bias", bias: "Candidate_B" },
  { id: "p2", name: "Creative Expansion", effect: "High Entropy / Multi-Branch", bias: "Candidate_D" },
  { id: "p3", name: "Balanced Audit", effect: "Deterministic / Trace-Heavy", bias: "Candidate_A" },
];

export default function SQIDemo() {
  const [isResolving, setIsResolving] = useState(false);
  const [hasCollapsed, setHasCollapsed] = useState(false);
  const [coherence, setCoherence] = useState(0.94);
  const [selectedPolicy, setSelectedPolicy] = useState(POLICIES[0]);
  const [activeNode, setActiveNode] = useState<number | null>(null);

  const triggerCollapse = () => {
    setIsResolving(true);
    setHasCollapsed(false);
    setTimeout(() => {
      setIsResolving(false);
      setHasCollapsed(true);
      setCoherence(0.31);
    }, 1800);
  };

  return (
    <div className="w-full space-y-12 animate-in fade-in duration-700">
      <div className="text-center space-y-6">
        <h1 className="text-7xl md:text-9xl font-bold tracking-tight text-black italic">SQI Runtime</h1>
        <p className="text-2xl text-gray-500 font-light tracking-tight">
          Symbolic Quantum Intelligence. <span className="text-black font-medium">Classical Hardware.</span>
        </p>
      </div>

      <div className="bg-white rounded-[3.5rem] shadow-2xl border border-gray-100 p-10">
        <div className="grid lg:grid-cols-2 gap-12">
          <div className="space-y-6">
            <div className="flex justify-between items-center px-4">
              <div className="flex flex-col">
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                  Coupling Graph (Entangled States)
                </span>
                <span className="text-[9px] text-blue-500 font-medium">Substrate: Symbolic MacBook Pro v1</span>
              </div>
              <div className="text-right">
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Coherence</span>
                <div className="text-xl font-mono font-bold text-black">{coherence.toFixed(2)}</div>
              </div>
            </div>

            <div className="h-[400px] bg-[#fafafa] rounded-[3rem] border border-gray-100 flex items-center justify-center relative overflow-hidden shadow-inner group">
              <svg className="absolute inset-0 w-full h-full p-20">
                <defs>
                  <filter id="glow">
                    <feGaussianBlur stdDeviation="2.5" result="coloredBlur" />
                    <feMerge>
                      <feMergeNode in="coloredBlur" />
                      <feMergeNode in="SourceGraphic" />
                    </feMerge>
                  </filter>
                </defs>

                <line
                  x1="20%"
                  y1="30%"
                  x2="80%"
                  y2="70%"
                  stroke={activeNode === 0 ? "#0071e3" : "#e5e7eb"}
                  strokeWidth="2"
                  strokeDasharray="4"
                  className="transition-colors duration-500"
                />
                <line
                  x1="80%"
                  y1="30%"
                  x2="20%"
                  y2="70%"
                  stroke={activeNode === 1 ? "#0071e3" : "#e5e7eb"}
                  strokeWidth="2"
                  strokeDasharray="4"
                  className="transition-colors duration-500"
                />

                {[
                  { x: "20%", y: "30%", label: "Domain_A" },
                  { x: "80%", y: "30%", label: "Domain_B" },
                  { x: "20%", y: "70%", label: "Policy_Gate" },
                  { x: "80%", y: "70%", label: "Outcome_Root" },
                ].map((node, idx) => (
                  <g key={idx} onMouseEnter={() => setActiveNode(idx)} onMouseLeave={() => setActiveNode(null)}>
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r="12"
                      className={`fill-white stroke-2 transition-all duration-500 ${
                        activeNode === idx ? "stroke-[#0071e3] scale-125" : "stroke-gray-300"
                      }`}
                      style={{ filter: activeNode === idx ? "url(#glow)" : "" }}
                    />
                    <text
                      x={node.x}
                      y={node.y}
                      dy="30"
                      textAnchor="middle"
                      className="text-[10px] font-mono fill-gray-400 uppercase tracking-tighter"
                    >
                      {node.label}
                    </text>
                  </g>
                ))}
              </svg>

              <div
                className={`absolute inset-0 flex flex-col items-center justify-center bg-white/90 backdrop-blur-xl transition-all duration-1000 ${
                  hasCollapsed ? "opacity-100 scale-100" : "opacity-0 scale-95 pointer-events-none"
                }`}
              >
                <div className="text-[10px] font-bold text-[#0071e3] uppercase tracking-widest mb-4">
                  State Collapsed under {selectedPolicy.name}
                </div>
                <div className="bg-black text-white px-12 py-5 rounded-full font-mono text-lg shadow-2xl tracking-tight">
                  {selectedPolicy.bias} <span className="text-gray-500 mx-2">|</span>{" "}
                  <span className="text-green-400">0.999α</span>
                </div>
                <button
                  onClick={() => {
                    setHasCollapsed(false);
                    setCoherence(0.94);
                  }}
                  className="mt-8 text-xs font-bold text-gray-400 hover:text-black transition-colors uppercase tracking-widest"
                >
                  Reset Wavefront
                </button>
              </div>

              {isResolving && (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/60 backdrop-blur-sm z-20">
                  <div className="w-12 h-12 border-2 border-[#0071e3] border-t-transparent rounded-full animate-spin mb-4" />
                  <span className="text-xs font-bold uppercase tracking-[0.3em] text-[#0071e3] animate-pulse">
                    Resolving Ambiguity
                  </span>
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-6">
            <div className="bg-[#0a0a0b] rounded-[3rem] p-10 text-white flex-1 flex flex-col justify-between shadow-2xl border border-white/5 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-blue-600/10 rounded-full blur-[60px]" />

              <div className="z-10">
                <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-8 flex justify-between">
                  <span>Policy/Observer Selection</span>
                  <span className="text-blue-500">SQI_RUNTIME_ACTIVE</span>
                </div>

                <div className="space-y-4">
                  {POLICIES.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => setSelectedPolicy(p)}
                      className={`w-full text-left p-6 rounded-3xl border transition-all duration-300 flex justify-between items-center group ${
                        selectedPolicy.id === p.id ? "border-[#0071e3] bg-blue-500/5" : "border-white/5 hover:border-white/20"
                      }`}
                    >
                      <div>
                        <div className={`text-sm font-bold transition-colors ${selectedPolicy.id === p.id ? "text-white" : "text-gray-400"}`}>
                          {p.name}
                        </div>
                        <div className="text-[10px] text-gray-600 mt-1 uppercase tracking-tighter">{p.effect}</div>
                      </div>
                      <div className={`w-2 h-2 rounded-full transition-all ${selectedPolicy.id === p.id ? "bg-[#0071e3] scale-125" : "bg-gray-800"}`} />
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={triggerCollapse}
                disabled={isResolving || hasCollapsed}
                className="w-full mt-10 bg-[#0071e3] text-white py-5 rounded-full font-bold text-xs hover:scale-[1.02] active:scale-95 transition-all uppercase tracking-[0.2em] shadow-lg shadow-blue-500/20 disabled:opacity-50 disabled:grayscale"
              >
                Trigger Governed Collapse
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* explainer block left as-is */}
      {/* ... keep the rest of your explainer section exactly the same ... */}
    </div>
  );
}
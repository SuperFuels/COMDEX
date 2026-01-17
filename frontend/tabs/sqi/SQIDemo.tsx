"use client";

import { useState } from "react";

const POLICIES = [
  { id: "p1", name: "Strict Compliance", effect: "Low Entropy / High Bias", bias: "Dedicated Server" },
  { id: "p2", name: "Creative Expansion", effect: "High Entropy / Multi-Branch", bias: "Shared Cluster" },
  { id: "p3", name: "Balanced Audit", effect: "Deterministic / Trace-Heavy", bias: "Shared Cluster" },
];

export default function SQIDemo() {
  const [isResolving, setIsResolving] = useState(false);
  const [hasCollapsed, setHasCollapsed] = useState(false);
  const [coherence, setCoherence] = useState(0.94);
  const [selectedPolicy, setSelectedPolicy] = useState(POLICIES[0]);
  const [activeNode, setActiveNode] = useState<number | null>(null);
  const [liveTrace, setLiveTrace] = useState<any>(null);
  const [showTrace, setShowTrace] = useState(false);

  const triggerCollapse = async () => {
    setIsResolving(true);
    setHasCollapsed(false);
    setLiveTrace(null);

    try {
      // LIVE API CALL TO YOUR BACKEND
      const response = await fetch("/api/sqi/demo/entangled_scheduler", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ policy: selectedPolicy.id }),
      });
      
      const data = await response.json();
      
      // Artificial delay to appreciate the "Resolution" phase
      setTimeout(() => {
        setLiveTrace(data);
        setCoherence(data.coherence_after);
        setIsResolving(false);
        setHasCollapsed(true);
      }, 1500);
    } catch (error) {
      console.error("SQI Runtime Error:", error);
      setIsResolving(false);
    }
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
          {/* LEFT: THE COUPLING GRAPH */}
          <div className="space-y-6">
            <div className="flex justify-between items-center px-4">
              <div className="flex flex-col">
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                  Coupling Graph (Entangled States)
                </span>
                <span className="text-[9px] text-blue-500 font-medium tracking-tight">LIVE BACKEND: /backend/modules/sqi</span>
              </div>
              <div className="text-right">
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Coherence Score</span>
                <div className="text-xl font-mono font-bold text-black">{coherence.toFixed(2)}</div>
              </div>
            </div>

            <div className="h-[400px] bg-[#fafafa] rounded-[3rem] border border-gray-100 flex items-center justify-center relative overflow-hidden shadow-inner group">
              <svg className="absolute inset-0 w-full h-full p-20">
                <defs>
                  <filter id="glow">
                    <feGaussianBlur stdDeviation="2.5" result="coloredBlur" />
                    <feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge>
                  </filter>
                </defs>

                {/* Entanglement Threads */}
                <line x1="20%" y1="30%" x2="80%" y2="70%" stroke={activeNode === 0 ? "#0071e3" : "#e5e7eb"} strokeWidth="2" strokeDasharray="4" className="transition-colors duration-500" />
                <line x1="80%" y1="30%" x2="20%" y2="70%" stroke={activeNode === 1 ? "#0071e3" : "#e5e7eb"} strokeWidth="2" strokeDasharray="4" className="transition-colors duration-500" />

                {[
                  { x: "20%", y: "30%", label: "TaskPriority" },
                  { x: "80%", y: "30%", label: "ResourceAlloc" },
                  { x: "20%", y: "70%", label: "Observer_Gate" },
                  { x: "80%", y: "70%", label: "Trace_Root" },
                ].map((node, idx) => (
                  <g key={idx} onMouseEnter={() => setActiveNode(idx)} onMouseLeave={() => setActiveNode(null)}>
                    <circle cx={node.x} cy={node.y} r="12" className={`fill-white stroke-2 transition-all duration-500 ${activeNode === idx ? "stroke-[#0071e3] scale-125" : "stroke-gray-300"}`} style={{ filter: activeNode === idx ? "url(#glow)" : "" }} />
                    <text x={node.x} y={node.y} dy="30" textAnchor="middle" className="text-[10px] font-mono fill-gray-400 uppercase tracking-tighter">{node.label}</text>
                  </g>
                ))}
              </svg>

              {/* COLLAPSED STATE OVERLAY */}
              <div className={`absolute inset-0 flex flex-col items-center justify-center bg-white/90 backdrop-blur-xl transition-all duration-1000 ${hasCollapsed ? "opacity-100 scale-100" : "opacity-0 scale-95 pointer-events-none"}`}>
                <div className="text-[10px] font-bold text-[#0071e3] uppercase tracking-widest mb-4">
                  Deterministic Collapse Verified
                </div>
                <div className="bg-black text-white px-10 py-5 rounded-full font-mono text-base shadow-2xl tracking-tight flex items-center gap-4">
                  <span className="text-gray-500">{liveTrace?.outcome.TaskPriority}</span>
                  <span className="text-blue-500">→</span>
                  <span className="text-green-400">{liveTrace?.outcome.ResourceAlloc}</span>
                </div>
                <div className="flex gap-4 mt-8">
                  <button onClick={() => { setHasCollapsed(false); setCoherence(0.94); setShowTrace(false); }} className="text-xs font-bold text-gray-400 hover:text-black transition-colors uppercase tracking-widest border-b border-transparent hover:border-black">
                    Reset State
                  </button>
                  <button onClick={() => setShowTrace(!showTrace)} className="text-xs font-bold text-[#0071e3] uppercase tracking-widest border-b border-transparent hover:border-[#0071e3]">
                    {showTrace ? "Hide Trace" : "View Audit Trace"}
                  </button>
                </div>
              </div>

              {isResolving && (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/60 backdrop-blur-sm z-20">
                  <div className="w-12 h-12 border-2 border-[#0071e3] border-t-transparent rounded-full animate-spin mb-4" />
                  <span className="text-xs font-bold uppercase tracking-[0.3em] text-[#0071e3] animate-pulse">Running SQI Backend...</span>
                </div>
              )}
            </div>
          </div>

          {/* RIGHT: POLICY CONTROLLER */}
          <div className="flex flex-col gap-6">
            <div className="bg-[#0a0a0b] rounded-[3rem] p-10 text-white flex-1 flex flex-col justify-between shadow-2xl border border-white/5 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-blue-600/10 rounded-full blur-[60px]" />
              <div className="z-10">
                <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-8 flex justify-between">
                  <span>Policy/Observer Selection</span>
                  <span className="text-blue-500">REALTIME_HARDWARE_MODE</span>
                </div>
                <div className="space-y-4">
                  {POLICIES.map((p) => (
                    <button key={p.id} onClick={() => setSelectedPolicy(p)} className={`w-full text-left p-6 rounded-3xl border transition-all duration-300 flex justify-between items-center group ${selectedPolicy.id === p.id ? "border-[#0071e3] bg-blue-500/5" : "border-white/5 hover:border-white/20"}`}>
                      <div>
                        <div className={`text-sm font-bold transition-colors ${selectedPolicy.id === p.id ? "text-white" : "text-gray-400"}`}>{p.name}</div>
                        <div className="text-[10px] text-gray-600 mt-1 uppercase tracking-tighter">{p.effect}</div>
                      </div>
                      <div className={`w-2 h-2 rounded-full transition-all ${selectedPolicy.id === p.id ? "bg-[#0071e3] scale-125" : "bg-gray-800"}`} />
                    </button>
                  ))}
                </div>
              </div>
              <button onClick={triggerCollapse} disabled={isResolving || hasCollapsed} className="w-full mt-10 bg-[#0071e3] text-white py-5 rounded-full font-bold text-xs hover:scale-[1.02] active:scale-95 transition-all uppercase tracking-[0.2em] shadow-lg shadow-blue-500/20 disabled:opacity-50">
                {isResolving ? "PROCESSING..." : "TRIGGER GOVERNED COLLAPSE"}
              </button>
            </div>
          </div>
        </div>

        {/* LIVE AUDIT TRACE VIEWER */}
        {showTrace && liveTrace && (
          <div className="mt-10 p-8 bg-[#0a0a0b] rounded-[2.5rem] border border-white/5 animate-in slide-in-from-top-4 duration-500">
            <div className="flex justify-between items-center mb-6">
              <h4 className="text-sm font-bold text-white uppercase tracking-widest italic">Black Box Flight Recorder</h4>
              <span className="text-[10px] font-mono text-gray-500">{liveTrace.demo_id}</span>
            </div>
            <div className="grid md:grid-cols-3 gap-8 mb-8">
              <TraceCaption step="Step 2" title="Entanglement Established" desc="Proving the link between Priority and Resources." />
              <TraceCaption step="Step 4" title="Semantic Teleportation" desc="Showing how resolving one side fixed the other." />
              <TraceCaption step="Final" title="Coherence Drop" desc="Proving the transition from Ambiguity to Certainty." />
            </div>
            <pre className="text-[11px] font-mono text-green-400/80 bg-black/40 p-6 rounded-2xl overflow-x-auto border border-white/5 leading-relaxed">
              {JSON.stringify(liveTrace, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* --- EXPLAINER SECTION (PITCH DECK) --- */}
      <div className="grid md:grid-cols-2 gap-16 mt-32 border-t border-gray-100 pt-24 pb-20">
        <div className="space-y-8">
          <div className="space-y-4">
            <h2 className="text-4xl font-bold italic tracking-tight text-black">Resolution Under Ambiguity</h2>
            <p className="text-lg text-gray-600 leading-relaxed font-light">
              Traditional computing is allergic to ambiguity; variables must be A or B. SQI (Symbolic Quantum Intelligence) treats **ambiguity as a first-class citizen.** </p>
            <p className="text-gray-500 leading-relaxed">
              In the demo above, Domain A and B are entangled via a Coupling Graph. When you select a Policy and trigger a collapse, SQI doesn't just "pick one"—it resolves the entire graph deterministically based on context and governance.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-6">
            <MetricCard label="Coherence Score" desc="A real-time signal of system stability. High coherence (0.9+) represents an unresolved state of potential; low coherence represents a settled outcome." />
            <MetricCard label="Drift Reports" desc="A structured report of incompleteness or unstable logic. If a state cannot collapse cleanly, SQI tells you exactly why and what logic is missing." />
          </div>
        </div>

        <div className="space-y-10">
          <div className="space-y-4">
            <h3 className="text-xl font-bold tracking-tight">The "MacBook" Supremacy</h3>
            <p className="text-sm text-gray-400 leading-relaxed">
              While the industry waits for the "$200M Quantum Fridge," GlyphOS delivers **Quantum-Inspired Logic on classical silicon.** By using formal semantics (SQM) instead of physical qubits, we enable superposition and entanglement in standard cloud containers.
            </p>
          </div>
          <div className="space-y-6">
            <h3 className="text-xl font-bold tracking-tight">Immediate Use Cases</h3>
            <div className="space-y-4">
              <UseCaseItem num="01" title="Regulated Decisioning" desc="Finance, legal triage, and compliance where every decision must be auditable." />
              <UseCaseItem num="02" title="Planning & Configuration" desc="Solving massive branching spaces with constraints and policy gates." />
              <UseCaseItem num="03" title="Knowledge Workflows" desc="Traceable reasoning and knowledge-graph materialization." />
            </div>
          </div>
          <div className="p-8 rounded-[2.5rem] bg-black text-white relative overflow-hidden">
             <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-500 mb-2">Standard of Truth</div>
             <p className="text-lg font-medium italic leading-snug relative z-10">
               "SQI doesn't replace the human observer; it gives the observer a governing substrate to collapse ambiguity into auditable, replayable truth."
             </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// SUB-COMPONENTS
function TraceCaption({ step, title, desc }: any) {
  return (
    <div className="space-y-1">
      <div className="text-[10px] font-bold text-[#0071e3] uppercase tracking-widest">{step}</div>
      <div className="text-xs font-bold text-white italic">{title}</div>
      <p className="text-[11px] text-gray-500 leading-tight">{desc}</p>
    </div>
  );
}

function MetricCard({ label, desc }: any) {
  return (
    <div className="p-8 bg-gray-50 rounded-[2.5rem] border border-gray-100">
      <div className="text-[10px] font-bold text-blue-600 uppercase mb-2">{label}</div>
      <p className="text-xs text-gray-500 leading-relaxed">{desc}</p>
    </div>
  );
}

function UseCaseItem({ num, title, desc }: any) {
  return (
    <div className="flex gap-4 items-start group">
      <span className="text-[#0071e3] font-mono font-bold mt-1">{num}</span>
      <div>
        <div className="text-sm font-bold text-black group-hover:text-[#0071e3] transition-colors">{title}</div>
        <div className="text-xs text-gray-500 mt-1">{desc}</div>
      </div>
    </div>
  );
}
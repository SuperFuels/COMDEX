"use client";

import { useState } from "react";
import { Card } from "@/tabs/Aion/demos/ui";

type ASTNode = {
  op: "atom" | "⊕" | "⊗" | "¬" | "∅";
  label?: string;
  children?: ASTNode[];
};

export default function PhotonHero() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentTheorem, setCurrentTheorem] = useState<"T8" | "T13">("T8");
  const [view, setView] = useState<"raw" | "canonical">("raw");

  const rawT8: ASTNode = {
    op: "⊗",
    children: [
      { op: "atom", label: "γ_alpha" },
      {
        op: "⊕",
        children: [
          { op: "atom", label: "γ_beta" },
          { op: "atom", label: "γ_delta" },
        ],
      },
    ],
  };

  const normT8: ASTNode = {
    op: "⊕",
    children: [
      {
        op: "⊗",
        children: [
          { op: "atom", label: "γ_alpha" },
          { op: "atom", label: "γ_beta" },
        ],
      },
      {
        op: "⊗",
        children: [
          { op: "atom", label: "γ_alpha" },
          { op: "atom", label: "γ_delta" },
        ],
      },
    ],
  };

  const rawT13: ASTNode = {
    op: "⊕",
    children: [
      { op: "atom", label: "a" },
      { op: "⊗", children: [{ op: "atom", label: "a" }, { op: "atom", label: "b" }] },
    ],
  };

  const normT13: ASTNode = { op: "atom", label: "a" };

  const runNormalize = () => {
    setIsProcessing(true);
    setTimeout(() => {
      setView("canonical");
      setIsProcessing(false);
    }, 800);
  };

  const reset = (thm: "T8" | "T13") => {
    setCurrentTheorem(thm);
    setView("raw");
  };

  const raw = currentTheorem === "T8" ? rawT8 : rawT13;
  const canonical = currentTheorem === "T8" ? normT8 : normT13;

  return (
    <div className="w-full space-y-8">
      <div className="flex justify-between items-center">
        <div className="flex gap-2">
          <button
            onClick={() => reset("T8")}
            className={`px-4 py-2 rounded-full text-xs font-bold transition-all ${
              currentTheorem === "T8" ? "bg-[#1B74E4] text-white" : "bg-slate-100 text-slate-500"
            }`}
          >
            T8: DISTRIBUTIVITY
          </button>
          <button
            onClick={() => reset("T13")}
            className={`px-4 py-2 rounded-full text-xs font-bold transition-all ${
              currentTheorem === "T13" ? "bg-[#1B74E4] text-white" : "bg-slate-100 text-slate-500"
            }`}
          >
            T13: ABSORPTION
          </button>
        </div>

        <div className="font-mono text-[10px] text-slate-400">
          LOCK_ID: <span className="text-slate-900 font-bold">PHOTON-PA-PHASE1</span>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        <Card title="Expression AST" subtitle="Raw Input Signal">
          <div className="min-h-[300px] flex flex-col justify-between">
            <div className="bg-slate-50 rounded-2xl p-6 border border-slate-100 font-mono text-sm overflow-auto">
              {view === "raw" ? (
                <ASTVisualizer node={raw} />
              ) : (
                <div className="flex items-center justify-center h-full text-slate-400 italic">
                  Normalization Complete.
                </div>
              )}
            </div>

            <button
              onClick={runNormalize}
              disabled={isProcessing || view === "canonical"}
              className="w-full mt-4 py-4 bg-slate-900 text-white rounded-2xl font-bold text-sm hover:bg-slate-800 disabled:opacity-50 transition-all uppercase tracking-widest"
            >
              {isProcessing ? "NORMALIZING..." : "Execute canonicalization"}
            </button>
          </div>
        </Card>

        <Card title="Canonical Form" subtitle="Lean Verified Output">
          <div className="min-h-[300px] bg-[#F8FAFC] rounded-2xl p-6 border border-[#1B74E4]/20 font-mono text-sm relative overflow-hidden">
            {view === "canonical" ? (
              <>
                <div className="absolute top-4 right-4 text-[10px] font-black text-emerald-500 bg-emerald-50 px-2 py-1 rounded">
                  PROVED
                </div>
                <ASTVisualizer node={canonical} color="#1B74E4" />
              </>
            ) : (
              <div className="flex items-center justify-center h-full text-slate-300 italic">
                Waiting for reduction...
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

function ASTVisualizer({ node, color = "#64748b" }: { node: ASTNode; color?: string }) {
  return (
    <div className="pl-4 border-l-2 border-slate-200 py-1">
      <div className="flex items-center gap-2">
        <span className="font-bold uppercase tracking-tighter" style={{ color }}>
          {node.op === "atom" ? node.label : node.op}
        </span>
      </div>
      {node.children?.length ? (
        <div className="mt-2 space-y-2">
          {node.children.map((child, i) => (
            <ASTVisualizer key={i} node={child} color={color} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
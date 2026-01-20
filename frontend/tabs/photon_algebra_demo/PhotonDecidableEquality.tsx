"use client";

import { useMemo, useState } from "react";
import { Card } from "@/tabs/Aion/demos/ui";

type Op = "atom" | "⊕" | "⊗" | "¬" | "∅" | "↔" | "★" | "⊖";
export type ASTNode = { op: Op; label?: string; children?: ASTNode[] };

type PresetId = "T8_equiv" | "T13_equiv" | "Different";

function canonKey(n: ASTNode): string {
  // stable structural key for equality (no styling, just shape)
  if (n.op === "atom") return `atom(${n.label ?? ""})`;
  const kids = (n.children ?? []).map(canonKey).join(",");
  return `${n.op}(${kids})`;
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

export default function PhotonDecidableEquality() {
  const [preset, setPreset] = useState<PresetId>("T8_equiv");
  const [isProcessing, setIsProcessing] = useState(false);
  const [view, setView] = useState<"raw" | "canonical">("raw");

  // --- Presets: two different raws, with shared canonical when "equiv" ---
  const { leftRaw, rightRaw, leftCanon, rightCanon } = useMemo(() => {
    // T8: a ⊗ (b ⊕ c)  vs  (a⊗b) ⊕ (a⊗c)
    const t8_left: ASTNode = {
      op: "⊗",
      children: [
        { op: "atom", label: "a" },
        { op: "⊕", children: [{ op: "atom", label: "b" }, { op: "atom", label: "c" }] },
      ],
    };
    const t8_right: ASTNode = {
      op: "⊕",
      children: [
        { op: "⊗", children: [{ op: "atom", label: "a" }, { op: "atom", label: "b" }] },
        { op: "⊗", children: [{ op: "atom", label: "a" }, { op: "atom", label: "c" }] },
      ],
    };
    const t8_canon = t8_right;

    // T13: a ⊕ (a ⊗ b)  vs  a
    const t13_left: ASTNode = {
      op: "⊕",
      children: [
        { op: "atom", label: "a" },
        { op: "⊗", children: [{ op: "atom", label: "a" }, { op: "atom", label: "b" }] },
      ],
    };
    const t13_right: ASTNode = { op: "atom", label: "a" };
    const t13_canon = t13_right;

    // Different: a vs b
    const diff_left: ASTNode = { op: "atom", label: "a" };
    const diff_right: ASTNode = { op: "atom", label: "b" };

    if (preset === "T8_equiv") {
      return { leftRaw: t8_left, rightRaw: t8_right, leftCanon: t8_canon, rightCanon: t8_canon };
    }
    if (preset === "T13_equiv") {
      return { leftRaw: t13_left, rightRaw: t13_right, leftCanon: t13_canon, rightCanon: t13_canon };
    }
    return { leftRaw: diff_left, rightRaw: diff_right, leftCanon: diff_left, rightCanon: diff_right };
  }, [preset]);

  const run = () => {
    setIsProcessing(true);
    setTimeout(() => {
      setView("canonical");
      setIsProcessing(false);
    }, 800);
  };

  const reset = (p: PresetId) => {
    setPreset(p);
    setView("raw");
  };

  const same = view === "canonical" && canonKey(leftCanon) === canonKey(rightCanon);

  return (
    <div className="w-full space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => reset("T8_equiv")}
            className={`px-4 py-2 rounded-full text-xs font-bold transition-all ${
              preset === "T8_equiv" ? "bg-[#1B74E4] text-white" : "bg-slate-100 text-slate-500 hover:bg-slate-200"
            }`}
          >
            Equivalence: T8
          </button>
          <button
            onClick={() => reset("T13_equiv")}
            className={`px-4 py-2 rounded-full text-xs font-bold transition-all ${
              preset === "T13_equiv" ? "bg-[#1B74E4] text-white" : "bg-slate-100 text-slate-500 hover:bg-slate-200"
            }`}
          >
            Equivalence: T13
          </button>
          <button
            onClick={() => reset("Different")}
            className={`px-4 py-2 rounded-full text-xs font-bold transition-all ${
              preset === "Different" ? "bg-[#1B74E4] text-white" : "bg-slate-100 text-slate-500 hover:bg-slate-200"
            }`}
          >
            Non-equivalent
          </button>
        </div>

        <div className="font-mono text-[10px] text-slate-400">
          MODE: <span className="text-slate-900 font-bold">DECIDABLE_EQUALITY</span>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        <Card title="Raw Signal A" subtitle="Input Form #1">
          <div className="min-h-[240px] bg-slate-50 rounded-2xl p-6 border border-slate-100 font-mono text-sm overflow-auto">
            {view === "raw" ? (
              <ASTVisualizer node={leftRaw} />
            ) : (
              <div className="flex items-center justify-center h-full text-slate-400 italic">Normalized.</div>
            )}
          </div>
        </Card>

        <Card title="Raw Signal B" subtitle="Input Form #2">
          <div className="min-h-[240px] bg-slate-50 rounded-2xl p-6 border border-slate-100 font-mono text-sm overflow-auto">
            {view === "raw" ? (
              <ASTVisualizer node={rightRaw} />
            ) : (
              <div className="flex items-center justify-center h-full text-slate-400 italic">Normalized.</div>
            )}
          </div>
        </Card>
      </div>

      <Card title="Canonical Verdict" subtitle="Unique Normal Form Comparison">
        <div className="grid lg:grid-cols-2 gap-8">
          <div className="min-h-[240px] bg-[#F8FAFC] rounded-2xl p-6 border border-[#1B74E4]/20 font-mono text-sm overflow-auto">
            {view === "canonical" ? (
              <ASTVisualizer node={leftCanon} color="#1B74E4" />
            ) : (
              <div className="flex items-center justify-center h-full text-slate-300 italic">Waiting…</div>
            )}
          </div>

          <div className="min-h-[240px] bg-[#F8FAFC] rounded-2xl p-6 border border-[#1B74E4]/20 font-mono text-sm overflow-auto relative">
            {view === "canonical" ? (
              <>
                <div
                  className={`absolute top-4 right-4 text-[10px] font-black px-2 py-1 rounded ${
                    same ? "text-emerald-600 bg-emerald-50" : "text-rose-600 bg-rose-50"
                  }`}
                >
                  {same ? "SAME" : "DIFFERENT"}
                </div>
                <ASTVisualizer node={rightCanon} color="#1B74E4" />
              </>
            ) : (
              <div className="flex items-center justify-center h-full text-slate-300 italic">Waiting…</div>
            )}
          </div>
        </div>

        <button
          onClick={run}
          disabled={isProcessing || view === "canonical"}
          className="w-full mt-6 py-4 bg-slate-900 text-white rounded-2xl font-bold text-sm hover:bg-slate-800 disabled:opacity-50 transition-all uppercase tracking-widest"
        >
          {isProcessing ? "NORMALIZING..." : "Normalize both + decide equality"}
        </button>
      </Card>
    </div>
  );
}
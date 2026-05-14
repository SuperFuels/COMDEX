"use client";

import { useMemo, useState } from "react";
import { Card } from "@/tabs/Aion/demos/ui";

/**
 * PhotonWorkbench.tsx
 * - Theorem Workbench: pick theorem → show Raw AST → "Execute canonicalization" → show Canonical AST
 * - Decidable Equality: two raws → normalize both → compare canonical structural key
 *
 * NOTE: This is UI-functional (mock normalize). Wire to backend normalize endpoint later.
 */

type Op = "atom" | "⊕" | "⊗" | "¬" | "∅" | "↔" | "★" | "⊖";

type ASTNode = {
  op: Op;
  label?: string;
  children?: ASTNode[];
};

type Thm = "T8" | "T11" | "T12" | "T13" | "T15";

type PresetId = "T8_equiv" | "T13_equiv" | "Different";

// ---------------------------
// helpers
// ---------------------------

function canonKey(n: ASTNode): string {
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

// ---------------------------
// Theorem Workbench
// ---------------------------

function PhotonTheoremWorkbench() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentTheorem, setCurrentTheorem] = useState<Thm>("T8");
  const [view, setView] = useState<"raw" | "canonical">("raw");

  const THEOREMS: Record<
    Thm,
    {
      title: string;
      subtitle: string;
      raw: ASTNode;
      canonical: ASTNode;
    }
  > = {
    T8: {
      title: "T8: DISTRIBUTIVITY",
      subtitle: "⊗ expands over ⊕",
      raw: {
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
      },
      canonical: {
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
      },
    },

    // (a ↔ a) → a
    T11: {
      title: "T11: ENTANGLEMENT IDEMPOTENCE",
      subtitle: "(a ↔ a) collapses to a",
      raw: {
        op: "↔",
        children: [{ op: "atom", label: "a" }, { op: "atom", label: "a" }],
      },
      canonical: { op: "atom", label: "a" },
    },

    // ★(a ↔ b) → (★a) ⊕ (★b)
    T12: {
      title: "T12: PROJECTION FIDELITY",
      subtitle: "★ distributes over ↔ into ⊕",
      raw: {
        op: "★",
        children: [
          {
            op: "↔",
            children: [{ op: "atom", label: "a" }, { op: "atom", label: "b" }],
          },
        ],
      },
      canonical: {
        op: "⊕",
        children: [
          { op: "★", children: [{ op: "atom", label: "a" }] },
          { op: "★", children: [{ op: "atom", label: "b" }] },
        ],
      },
    },

    // a ⊕ (a ⊗ b) → a
    T13: {
      title: "T13: ABSORPTION",
      subtitle: "a ⊕ (a ⊗ b) collapses to a",
      raw: {
        op: "⊕",
        children: [
          { op: "atom", label: "a" },
          {
            op: "⊗",
            children: [{ op: "atom", label: "a" }, { op: "atom", label: "b" }],
          },
        ],
      },
      canonical: { op: "atom", label: "a" },
    },

    // a ⊖ a → ∅
    T15: {
      title: "T15: CANCELLATION",
      subtitle: "a ⊖ a deletes to ∅",
      raw: {
        op: "⊖",
        children: [{ op: "atom", label: "a" }, { op: "atom", label: "a" }],
      },
      canonical: { op: "∅" },
    },
  };

  const runNormalize = () => {
    setIsProcessing(true);
    setTimeout(() => {
      setView("canonical");
      setIsProcessing(false);
    }, 800);
  };

  const reset = (thm: Thm) => {
    setCurrentTheorem(thm);
    setView("raw");
  };

  const { raw, canonical } = THEOREMS[currentTheorem];

  const buttons: Array<{ key: Thm }> = [
    { key: "T8" },
    { key: "T11" },
    { key: "T12" },
    { key: "T13" },
    { key: "T15" },
  ];

  return (
    <div className="w-full space-y-8">
      <div className="flex justify-between items-center gap-4 flex-wrap">
        <div className="flex gap-2 flex-wrap">
          {buttons.map((b) => (
            <button
              key={b.key}
              onClick={() => reset(b.key)}
              className={`px-4 py-2 rounded-full text-xs font-bold transition-all ${
                currentTheorem === b.key
                  ? "bg-[#1B74E4] text-white"
                  : "bg-slate-100 text-slate-500 hover:bg-slate-200"
              }`}
              title={THEOREMS[b.key].subtitle}
            >
              {THEOREMS[b.key].title}
            </button>
          ))}
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

// ---------------------------
// Decidable Equality Panel
// ---------------------------

function PhotonDecidableEquality() {
  const [preset, setPreset] = useState<PresetId>("T8_equiv");
  const [isProcessing, setIsProcessing] = useState(false);
  const [view, setView] = useState<"raw" | "canonical">("raw");

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

// ---------------------------
// Workbench container
// ---------------------------

export default function PhotonWorkbench() {
  return (
    <div className="w-full space-y-10">
      <PhotonTheoremWorkbench />
      <PhotonDecidableEquality />
    </div>
  );
}
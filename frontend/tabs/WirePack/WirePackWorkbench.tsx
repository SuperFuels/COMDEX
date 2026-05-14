"use client";

// WirePackWorkbench.tsx
// Workbench shell (tabs + dropdown). Demos live in src/glyphnet/routes/protocols/*
// Branded to match SLE/RQC light aesthetic (F8FAFC bg, white cards, slate text, blue accent)

import React, { useEffect, useMemo, useState } from "react";

import { V10StreamingTransportDemo } from "../../src/glyphnet/routes/protocols/V10StreamingTransportDemo";
import { V12MultiTemplateCatalogDemo } from "../../src/glyphnet/routes/protocols/V12MultiTemplateCatalogDemo";
import { V29ProjectionDemo } from "../../src/glyphnet/routes/protocols/V29ProjectionDemo";
import { V30SumOverQDemo } from "../../src/glyphnet/routes/protocols/V30SumOverQDemo";
import { V32HeavyHittersDemo } from "../../src/glyphnet/routes/protocols/V32HeavyHittersDemo";
import { V33RangeSumsDemo } from "../../src/glyphnet/routes/protocols/V33RangeSumsDemo";
import { V34HistogramDemo } from "../../src/glyphnet/routes/protocols/V34HistogramDemo";
import { V38TrustReceiptsDemo } from "../../src/glyphnet/routes/protocols/V38TrustReceiptsDemo";
import { V41ReceiptGatedQueriesDemo } from "../../src/glyphnet/routes/protocols/V41ReceiptGatedQueriesDemo";
import { V44SqlOnStreamsDemo } from "../../src/glyphnet/routes/protocols/V44SqlOnStreamsDemo";
import { V45CrossLanguageVectorsDemo } from "../../src/glyphnet/routes/protocols/V45CrossLanguageVectorsDemo";
import { V46StreamingTransportDemo } from "../../src/glyphnet/routes/protocols/V46StreamingTransportDemo";

type TabId = "transport" | "analytics" | "trust";

type DemoId =
  | "v46_transport_streaming"
  | "v10_streaming_transport"
  | "v12_multi_template_catalog"
  | "v44_sql_on_streams"
  | "v32_heavy_hitters"
  | "v29_projection_q"
  | "v30_sum_over_q"
  | "v33_range_sums"
  | "v34_histogram"
  | "v41_receipt_gated_queries"
  | "v45_cross_language_vectors"
  | "v38_trust_receipts";

type DemoMeta = {
  id: DemoId;
  tab: TabId;
  title: string;
  blurb: string;
  Component: React.ComponentType;
};

function TabButton(props: {
  active: boolean;
  onClick: () => void;
  children: any;
}) {
  return (
    <button
      type="button"
      onClick={props.onClick}
      className={[
        "px-4 py-2 rounded-full text-xs font-semibold transition-all border",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1B74E4]/30",
        props.active
          ? "bg-[#1B74E4] text-white border-[#1B74E4] shadow-sm"
          : "bg-white text-slate-800 border-slate-200 hover:bg-slate-50",
      ].join(" ")}
    >
      {props.children}
    </button>
  );
}

// Error boundary (so “white page” becomes a visible error)
class DemoErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { err: any }
> {
  state = { err: null as any };
  static getDerivedStateFromError(err: any) {
    return { err };
  }
  componentDidCatch(err: any) {
    // eslint-disable-next-line no-console
    console.error("Demo crashed:", err);
  }
  render() {
    if (this.state.err) {
      return (
        <div className="rounded-2xl border border-red-200 bg-white p-4 shadow-sm">
          <div className="text-sm font-extrabold text-red-800">
            Demo crashed during render
          </div>
          <pre className="mt-2 text-xs text-slate-900 whitespace-pre-wrap">
            {String(
              this.state.err?.stack ||
                this.state.err?.message ||
                this.state.err,
            )}
          </pre>
        </div>
      );
    }
    return this.props.children as any;
  }
}

export default function WirePackWorkbench() {
  const demos: DemoMeta[] = useMemo(
    () => [
      // -------- Transport --------
      {
        id: "v46_transport_streaming",
        tab: "transport",
        title: "v46 — Streaming transport",
        blurb:
          "Template once + deltas (real endpoints) vs gzip-per-frame baseline.",
        Component: V46StreamingTransportDemo,
      },
      {
        id: "v10_streaming_transport",
        tab: "transport",
        title: "v10 — Streaming transport",
        blurb:
          "Template cache + deltas + MTU packet estimate + deterministic receipt (real endpoints).",
        Component: V10StreamingTransportDemo,
      },
      {
        id: "v12_multi_template_catalog",
        tab: "transport",
        title: "v12 — Multi-template catalog",
        blurb:
          "Multiple templates cached + selected; real-world shape variability; receipt per template.",
        Component: V12MultiTemplateCatalogDemo,
      },

      // -------- Analytics --------
      {
        id: "v44_sql_on_streams",
        tab: "analytics",
        title: "v44 — SQL on streams",
        blurb: "Query-on-stream analytics.",
        Component: V44SqlOnStreamsDemo,
      },
      {
        id: "v32_heavy_hitters",
        tab: "analytics",
        title: "v32 — Heavy hitters (Top-K)",
        blurb: "Top-K activity on compressed streams + verifiable receipt.",
        Component: V32HeavyHittersDemo,
      },
      {
        id: "v29_projection_q",
        tab: "analytics",
        title: "v29 — Projection(Q)",
        blurb:
          "Track only |Q| indices and still match full replay (receipt-locked).",
        Component: V29ProjectionDemo,
      },
      {
        id: "v30_sum_over_q",
        tab: "analytics",
        title: "v30 — Sum over Q",
        blurb:
          "Maintain SUM over a query set Q incrementally; matches full replay (receipt-locked).",
        Component: V30SumOverQDemo,
      },
      {
        id: "v33_range_sums",
        tab: "analytics",
        title: "v33 — Range sums (L..R)",
        blurb:
          "Interval queries without scanning; streaming range sum is O(log n) (receipt-locked).",
        Component: V33RangeSumsDemo,
      },
      {
        id: "v34_histogram",
        tab: "analytics",
        title: "v34 — Histogram (modulus / buckets)",
        blurb: "Distribution queries on stream; hist_ok=true.",
        Component: V34HistogramDemo,
      },

      // -------- Trust --------
      {
        id: "v41_receipt_gated_queries",
        tab: "trust",
        title: "v41 — Receipt-gated queries",
        blurb:
          "You can’t query unless the receipt chain verifies (anti demo-theater).",
        Component: V41ReceiptGatedQueriesDemo,
      },
      {
        id: "v45_cross_language_vectors",
        tab: "trust",
        title: "v45 — Cross-language vectors",
        blurb:
          "Byte-identical template+delta across implementations + stable final hash.",
        Component: V45CrossLanguageVectorsDemo,
      },
      {
        id: "v38_trust_receipts",
        tab: "trust",
        title: "v38 — Trust & receipts",
        blurb:
          "Canonical bytes + replay invariants + deterministic receipts (real endpoint).",
        Component: V38TrustReceiptsDemo,
      },
    ],
    [],
  );

  const [tab, setTab] = useState<TabId>("transport");
  const demosForTab = demos.filter((d) => d.tab === tab);

  const [demoId, setDemoId] = useState<DemoId>("v46_transport_streaming");

  useEffect(() => {
    // keep demoId valid when switching tabs
    const allowed = demosForTab.map((d) => d.id);
    if (!allowed.includes(demoId))
      setDemoId(demosForTab[0]?.id || "v46_transport_streaming");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  const active = demos.find((d) => d.id === demoId) || demos[0];
  const ActiveDemo = active.Component;

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 selection:bg-[#1B74E4]/10">
      <div className="mx-auto max-w-7xl px-6 py-12">
        {/* Hero */}
        <header className="mb-10 border-l-4 border-[#1B74E4] pl-6">
          <div className="text-xs font-bold uppercase tracking-widest text-slate-400">
            WirePack Protocol Workbench
          </div>
          <h1 className="mt-2 text-4xl font-black tracking-tighter text-slate-900">
            Template + Delta Streaming
          </h1>
          <p className="mt-4 max-w-2xl text-sm font-medium leading-relaxed text-slate-600">
            {active.blurb}
          </p>

          <div className="mt-4 flex flex-wrap items-center gap-2 text-[11px] font-semibold text-slate-500">
            <span className="rounded-full border border-slate-200 bg-white px-3 py-1">
              Track:{" "}
              <span className="font-mono text-slate-700">{tab}</span>
            </span>
            <span className="rounded-full border border-slate-200 bg-white px-3 py-1">
              Demo:{" "}
              <span className="font-mono text-slate-700">{active.title}</span>
            </span>
          </div>
        </header>

        {/* Workbench Card */}
        <div className="rounded-[2.5rem] border border-slate-200 bg-white p-8 shadow-sm">
          {/* Controls */}
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="text-xs font-bold uppercase tracking-widest text-slate-400">
                Demo Selector
              </div>
              <div className="mt-1 text-sm font-semibold text-slate-800">
                Choose a protocol demo
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <TabButton
                active={tab === "transport"}
                onClick={() => setTab("transport")}
              >
                Transport
              </TabButton>
              <TabButton
                active={tab === "analytics"}
                onClick={() => setTab("analytics")}
              >
                Analytics
              </TabButton>
              <TabButton active={tab === "trust"} onClick={() => setTab("trust")}>
                Trust
              </TabButton>

              <select
                value={demoId}
                onChange={(e) => setDemoId(e.target.value as DemoId)}
                className={[
                  "px-4 py-2 rounded-full text-xs font-semibold border",
                  "border-slate-200 bg-white text-slate-800",
                  "focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1B74E4]/30",
                ].join(" ")}
              >
                {demosForTab.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.title}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Demo surface */}
          <div className="mt-6 rounded-3xl border border-slate-100 bg-[#fafafa] p-6">
            <DemoErrorBoundary>
              <ActiveDemo />
            </DemoErrorBoundary>
          </div>

          {/* Footer hint */}
          <div className="mt-6 text-xs text-slate-500">
            Tip: start with <span className="font-mono text-slate-700">v46</span>{" "}
            (real streaming baseline), then move to{" "}
            <span className="font-mono text-slate-700">v41</span> for the
            receipt-gated trust story.
          </div>
        </div>
      </div>
    </div>
  );
}
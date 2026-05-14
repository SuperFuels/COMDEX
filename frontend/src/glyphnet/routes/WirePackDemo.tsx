// WirePackDemo.tsx (FULL FILE REPLACEMENT)
// Demo shell (tabs + dropdown). All demos live in ./protocols/*

import React, { useEffect, useMemo, useState } from "react";

import { V44SqlOnStreamsDemo } from "./protocols/V44SqlOnStreamsDemo";
import { V38TrustReceiptsDemo } from "./protocols/V38TrustReceiptsDemo";
import { V45CrossLanguageVectorsDemo } from "./protocols/V45CrossLanguageVectorsDemo";
import { V32HeavyHittersDemo } from "./protocols/V32HeavyHittersDemo";
import { V10StreamingTransportDemo } from "./protocols/V10StreamingTransportDemo";
import { V29ProjectionDemo } from "./protocols/V29ProjectionDemo";
import { V30SumOverQDemo } from "./protocols/V30SumOverQDemo";
import { V33RangeSumsDemo } from "./protocols/V33RangeSumsDemo";
import { V41ReceiptGatedQueriesDemo } from "./protocols/V41ReceiptGatedQueriesDemo";
import { V12MultiTemplateCatalogDemo } from "./protocols/V12MultiTemplateCatalogDemo";
import { V46StreamingTransportDemo } from "./protocols/V46StreamingTransportDemo";
import { V34HistogramDemo } from "./protocols/V34HistogramDemo";

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

function TabButton(props: { active: boolean; onClick: () => void; children: any }) {
  return (
    <button
      type="button"
      onClick={props.onClick}
      style={{
        padding: "6px 10px",
        borderRadius: 999,
        border: "1px solid " + (props.active ? "#111827" : "#e5e7eb"),
        background: props.active ? "#111827" : "#fff",
        color: props.active ? "#fff" : "#111827",
        fontSize: 11,
        fontWeight: 700,
        cursor: "pointer",
      }}
    >
      {props.children}
    </button>
  );
}

// Error boundary (so “white page” becomes a visible error)
class DemoErrorBoundary extends React.Component<{ children: React.ReactNode }, { err: any }> {
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
        <div style={{ borderRadius: 14, border: "1px solid #fecaca", background: "#fff", padding: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 900, color: "#991b1b" }}>Demo crashed during render</div>
          <pre style={{ marginTop: 8, fontSize: 11, color: "#111827", whiteSpace: "pre-wrap" }}>
            {String(this.state.err?.stack || this.state.err?.message || this.state.err)}
          </pre>
        </div>
      );
    }
    return this.props.children as any;
  }
}

export default function WirePackDemo() {
  const demos: DemoMeta[] = useMemo(
    () => [
      // -------- Transport --------
      {
        id: "v46_transport_streaming",
        tab: "transport",
        title: "v46 — Streaming transport",
        blurb: "Template once + deltas (real endpoints) vs gzip-per-frame baseline.",
        Component: V46StreamingTransportDemo,
      },
      {
        id: "v10_streaming_transport",
        tab: "transport",
        title: "v10 — Streaming transport",
        blurb: "Template cache + deltas + MTU packet estimate + deterministic receipt (real endpoints).",
        Component: V10StreamingTransportDemo,
      },
      {
        id: "v12_multi_template_catalog",
        tab: "transport",
        title: "v12 — Multi-template catalog",
        blurb: "Multiple templates cached + selected; real-world shape variability; receipt per template.",
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
        blurb: "Track only |Q| indices and still match full replay (receipt-locked).",
        Component: V29ProjectionDemo,
      },
      {
        id: "v30_sum_over_q",
        tab: "analytics",
        title: "v30 — Sum over Q",
        blurb: "Maintain SUM over a query set Q incrementally; matches full replay (receipt-locked).",
        Component: V30SumOverQDemo,
      },
      {
        id: "v33_range_sums",
        tab: "analytics",
        title: "v33 — Range sums (L..R)",
        blurb: "Interval queries without scanning; streaming range sum is O(log n) (receipt-locked).",
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
        blurb: "You can’t query unless the receipt chain verifies (anti demo-theater).",
        Component: V41ReceiptGatedQueriesDemo,
      },
      {
        id: "v45_cross_language_vectors",
        tab: "trust",
        title: "v45 — Cross-language vectors",
        blurb: "Byte-identical template+delta across implementations + stable final hash.",
        Component: V45CrossLanguageVectorsDemo,
      },
      {
        id: "v38_trust_receipts",
        tab: "trust",
        title: "v38 — Trust & receipts",
        blurb: "Canonical bytes + replay invariants + deterministic receipts (real endpoint).",
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
    if (!allowed.includes(demoId)) setDemoId(demosForTab[0]?.id || "v46_transport_streaming");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  const active = demos.find((d) => d.id === demoId) || demos[0];
  const ActiveDemo = active.Component;

  return (
    <div style={{ padding: 14, background: "#f9fafb", minHeight: "100vh" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 900, color: "#111827" }}>WirePack demos</div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>{active.blurb}</div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <TabButton active={tab === "transport"} onClick={() => setTab("transport")}>
            Transport
          </TabButton>
          <TabButton active={tab === "analytics"} onClick={() => setTab("analytics")}>
            Analytics
          </TabButton>
          <TabButton active={tab === "trust"} onClick={() => setTab("trust")}>
            Trust
          </TabButton>

          <select
            value={demoId}
            onChange={(e) => setDemoId(e.target.value as DemoId)}
            style={{ padding: "6px 10px", borderRadius: 999, border: "1px solid #e5e7eb", background: "#fff", fontSize: 11 }}
          >
            {demosForTab.map((d) => (
              <option key={d.id} value={d.id}>
                {d.title}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div style={{ marginTop: 12 }}>
        <DemoErrorBoundary>
          <ActiveDemo />
        </DemoErrorBoundary>
      </div>
    </div>
  );
}
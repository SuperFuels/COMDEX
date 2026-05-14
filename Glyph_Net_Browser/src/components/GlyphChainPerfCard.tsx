import React, { useEffect, useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

type PerfPoint = {
  ts: string;
  tps: number;
  lat_ms?: { p95?: number };
};

const LS_KEY = "glyphchainPerfHistory";

function loadHistory(): PerfPoint[] {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return [];
    const xs = JSON.parse(raw);
    return Array.isArray(xs) ? xs : [];
  } catch {
    return [];
  }
}

function saveHistory(xs: PerfPoint[]) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(xs.slice(-200)));
  } catch {}
}

export function GlyphChainPerfCard() {
  const [latest, setLatest] = useState<PerfPoint | null>(null);
  const [history, setHistory] = useState<PerfPoint[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setHistory(loadHistory());

    let cancelled = false;

    (async () => {
      try {
        setErr(null);
        const r = await fetch("/api/glyphchain/dev/perf/latest", {
          headers: { Accept: "application/json" },
        });

        if (!r.ok) {
          const txt = await r.text().catch(() => "");
          throw new Error(txt || `HTTP ${r.status} ${r.statusText}`);
        }

        const j = await r.json();
        const d = j?.data;

        if (!d?.ts || typeof d?.tps !== "number") return;

        const point: PerfPoint = {
          ts: d.ts,
          tps: d.tps,
          lat_ms: d.lat_ms,
        };

        if (cancelled) return;
        setLatest(point);

        setHistory((prev) => {
          const next = [...prev];
          if (!next.some((x) => x.ts === point.ts)) next.push(point);
          saveHistory(next);
          return next;
        });
      } catch (e: any) {
        if (!cancelled) setErr(e?.message || "Failed to load perf");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const points = useMemo(
    () =>
      history.map((h) => ({
        ts: h.ts,
        tps: h.tps,
        p95: h.lat_ms?.p95 ?? 0,
      })),
    [history],
  );

  const latestP95 =
    latest?.lat_ms?.p95 != null ? `${latest.lat_ms.p95.toFixed(2)} ms` : "—";

  return (
    <section
      style={{
        borderRadius: 16,
        border: "1px solid #e5e7eb",
        background: "#ffffff",
        padding: 14,
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          gap: 12,
        }}
      >
        <div>
          <div style={{ fontSize: 12, color: "#6b7280", fontWeight: 600 }}>
            GlyphChain Performance (dev)
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#0f172a" }}>
            {latest ? `${latest.tps.toFixed(2)} TPS` : "—"}
          </div>
          <div style={{ fontSize: 11, color: "#6b7280" }}>p95: {latestP95}</div>
        </div>

        <div style={{ fontSize: 11, color: "#9ca3af" }}>
          points: {history.length}
        </div>
      </div>

      {err && (
        <div style={{ fontSize: 11, color: "#b91c1c" }}>
          {err}
        </div>
      )}

      <div
        style={{
          width: "100%",
          height: 220, // ✅ give it height
          minWidth: 0, // ✅ fixes flex/grid shrink issues
          borderRadius: 12,
          border: "1px solid #e5e7eb",
          background: "#f9fafb",
          padding: 8,
        }}
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points}>
            <XAxis
              dataKey="ts"
              hide
              tickFormatter={(v) => String(v).slice(11, 19)}
            />
            <YAxis />
            <Tooltip
              labelFormatter={(v) => String(v)}
              formatter={(val: any, name: any) => [val, name]}
            />
            <Line type="monotone" dataKey="tps" dot={false} />
            <Line type="monotone" dataKey="p95" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div style={{ fontSize: 11, color: "#6b7280" }}>
        Tip: run{" "}
        <span style={{ fontFamily: "monospace" }}>
          CHAIN_SIM_TXN=1000 pytest -q -s backend/tests/test_chain_sim_perf.py
        </span>{" "}
        then refresh.
      </div>
    </section>
  );
}
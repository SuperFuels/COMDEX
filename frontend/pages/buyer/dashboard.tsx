// /workspaces/COMDEX/frontend/tabs/buyer/Dashboard.tsx
"use client";

import React, { useEffect, useRef, useState } from "react";
import useAuthRedirect from "@/hooks/useAuthRedirect";
import api from "@/lib/api";
import Chart, { ChartPoint } from "@/components/Chart";

interface BuyerMetrics {
  totalSalesToday: number;
  openOrders: number;
  pendingEscrow: number;
  availableProducts: number;
  activeDeals: number;
}

const METRICS: Array<{ key: keyof BuyerMetrics; label: string; color: string }> = [
  { key: "totalSalesToday", label: "Sales Today", color: "text-blue-600" },
  { key: "openOrders", label: "Open Orders", color: "text-green-600" },
  { key: "pendingEscrow", label: "Pending Escrow", color: "text-purple-600" },
  { key: "availableProducts", label: "Available Products", color: "text-green-600" },
  { key: "activeDeals", label: "Active Deals", color: "text-blue-600" },
];

const COMMAND_TABS = ["Deal Flow", "Shipments", "Messages", "Escrow", "Contracts", "Suppliers", "Products"];

export default function BuyerDashboard() {
  useAuthRedirect("buyer");

  // ── Metrics
  const [metrics, setMetrics] = useState<BuyerMetrics | null>(null);
  const [loadingMetrics, setLoadingMetrics] = useState(true);
  const [errorMetrics, setErrorMetrics] = useState<string | null>(null);

  // ── Terminal state
  const [queryText, setQueryText] = useState("");
  const [analysisText, setAnalysisText] = useState("");
  const [chartData, setChartData] = useState<ChartPoint[] | null>(null);
  const [searchResults, setSearchResults] = useState<any[] | null>(null);
  const [nextPage, setNextPage] = useState<number | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  // ── Split-pane
  const containerRef = useRef<HTMLDivElement>(null);
  const [dividerX, setDividerX] = useState(0);
  const dragging = useRef(false);

  // Init divider
  useEffect(() => {
    const w = containerRef.current?.clientWidth ?? 0;
    if (w) setDividerX(w / 2);
  }, []);

  // Keep divider sane on resize
  useEffect(() => {
    const onResize = () => {
      if (!containerRef.current) return;
      const w = containerRef.current.clientWidth;
      setDividerX((prev) => {
        const min = w * 0.25;
        const max = w * 0.75;
        const next = prev || w / 2;
        return Math.max(min, Math.min(max, next));
      });
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  // Drag handlers (capture + prevent “stuck drag” and accidental text selection)
  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current || !containerRef.current) return;
      e.preventDefault();
      const { left, width } = containerRef.current.getBoundingClientRect();
      let x = e.clientX - left;
      const min = width * 0.25;
      const max = width * 0.75;
      x = Math.max(min, Math.min(max, x));
      setDividerX(x);
    };

    const onUp = () => {
      dragging.current = false;
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };

    window.addEventListener("mousemove", onMove, { passive: false });
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove as any);
      window.removeEventListener("mouseup", onUp);
    };
  }, []);

  const onDividerDown = (e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;
    document.body.style.userSelect = "none";
    document.body.style.cursor = "col-resize";
  };

  // ── Fetch buyer metrics
  useEffect(() => {
    let active = true;
    setLoadingMetrics(true);
    setErrorMetrics(null);

    api
      .get<BuyerMetrics>("/buyer/dashboard")
      .then((r) => {
        if (!active) return;
        setMetrics(r.data);
      })
      .catch(() => {
        // Don’t hard-fail UI; default zeros (matches your existing behavior)
        if (!active) return;
        console.warn("Metrics fetch failed; defaulting zeros.");
        setMetrics({
          totalSalesToday: 0,
          openOrders: 0,
          pendingEscrow: 0,
          availableProducts: 0,
          activeDeals: 0,
        });
      })
      .finally(() => {
        if (!active) return;
        setLoadingMetrics(false);
      });

    return () => {
      active = false;
    };
  }, []);

  // ── Terminal send
  const sendQuery = async (forced?: string) => {
    const prompt = (forced ?? queryText).trim();
    if (!prompt) return;

    setIsProcessing(true);
    setAnalysisText("");
    setChartData(null);
    setSearchResults(null);
    setNextPage(null);

    try {
      const base = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, "");
      const resp = await fetch(`${base}/terminal/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });

      const json = await resp.json().catch(() => ({} as any));
      setAnalysisText(json.analysisText || "");

      const vp = json.visualPayload || {};
      if (Array.isArray(vp.products)) {
        setSearchResults(vp.products);
        setNextPage((vp as any).nextPage ?? null);
      } else if (Array.isArray(vp.chartData)) {
        setChartData(vp.chartData as ChartPoint[]);
      }
    } catch {
      setAnalysisText("❌ Something went wrong. Please try again.");
    } finally {
      setIsProcessing(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendQuery();
    }
  };

  const onTabClick = (label: string) => {
    setQueryText(label);
    // Use the label directly so we don’t race React state
    setTimeout(() => void sendQuery(label), 0);
  };

  const loadMore = async () => {
    if (!nextPage) return;
    setIsProcessing(true);
    try {
      const resp = await api.get<any[]>(
        `/products?search=${encodeURIComponent(queryText)}&limit=10&page=${nextPage}`,
      );
      const more = resp.data || [];
      setSearchResults((prev) => (prev ? [...prev, ...more] : more));
      setNextPage(more.length === 10 ? nextPage + 1 : null);
    } finally {
      setIsProcessing(false);
    }
  };

  // ── Render
  if (loadingMetrics) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <p>Loading…</p>
      </div>
    );
  }

  if (errorMetrics || !metrics) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <p className="text-red-500">{errorMetrics || "Failed to load metrics"}</p>
      </div>
    );
  }

  const m = metrics;

  return (
    <div className="bg-gray-50 min-h-screen flex flex-col">
      <main className="flex-1 max-w-[calc(100%-40px)] mx-auto px-4">
        <div ref={containerRef} className="relative flex h-[calc(100vh-8rem)]">
          {/* Left Pane */}
          <div className="overflow-auto pr-4 font-mono text-gray-800 text-sm" style={{ width: dividerX }}>
            <p className="mb-2">Hello, Buyer — welcome.</p>
            {METRICS.map((mt) => (
              <p key={mt.key} className="mb-1">
                <span>“{mt.label}”: </span>
                <span className={mt.color}>{m[mt.key]}</span>
              </p>
            ))}

            {analysisText && (
              <div className="mt-4 space-y-1">
                {analysisText.split("\n").map((l, i) => (
                  <p key={i}>{l}</p>
                ))}
              </div>
            )}
          </div>

          {/* Divider */}
          <div
            onMouseDown={onDividerDown}
            className="bg-gray-300 hover:bg-blue-500"
            style={{ cursor: "col-resize", width: 6, marginLeft: -3, zIndex: 10 }}
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize panes"
          />

          {/* Right Pane */}
          <div className="flex-1 overflow-auto pl-4">
            {searchResults ? (
              <>
                {searchResults.map((p, i) => (
                  <div key={i} className="bg-white p-3 rounded shadow mb-2 flex items-center space-x-3">
                    <img
                      src={`${process.env.NEXT_PUBLIC_API_URL || ""}${p.image_url}`}
                      alt={p.title}
                      className="h-16 w-16 object-cover rounded"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = "/placeholder.jpg";
                      }}
                    />
                    <div>
                      <h3 className="font-semibold">{p.title}</h3>
                      <p className="text-sm">{p.description}</p>
                      <p className="text-sm">
                        £{p.price_per_kg}/kg · {p.origin_country}
                      </p>
                    </div>
                  </div>
                ))}

                {nextPage && (
                  <button onClick={loadMore} disabled={isProcessing} className="px-4 py-2 border rounded">
                    {isProcessing ? "Loading…" : "Next Page"}
                  </button>
                )}
              </>
            ) : chartData && chartData.length > 0 ? (
              <Chart data={chartData} height={(containerRef.current?.clientHeight ?? 0) - 64} />
            ) : (
              <div className="h-full flex items-center justify-center text-gray-500">
                <p>Ask a question or pick a tab to see data here.</p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 w-full bg-white border-t py-4">
        <div className="max-w-[calc(100%-40px)] mx-auto px-4 flex">
          <div className="flex items-center space-x-2" style={{ width: Math.max(240, dividerX - 20) }}>
            <input
              type="text"
              placeholder="Type a question…"
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              onKeyDown={onKeyDown}
              className="flex-1 py-2 px-4 border rounded"
            />
            <button onClick={() => void sendQuery()} disabled={isProcessing} className="py-2 px-4 bg-black text-white rounded">
              {isProcessing ? "Working…" : "Send"}
            </button>
          </div>

          <div className="flex-1 flex justify-end space-x-2">
            {COMMAND_TABS.map((label) => (
              <button key={label} onClick={() => onTabClick(label)} className="px-3 py-1 border rounded text-sm">
                {label}
              </button>
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
}
"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import useAuthRedirect from "@/hooks/useAuthRedirect";
import Chart, { ChartPoint } from "@/components/Chart";

// Types

// Supplier
type SupplierMetrics = {
  totalSalesToday: number;
  activeListings: number;
  openOrders: number;
  proceeds30d: number;
  feedbackRating: number;
};

// AION
type Milestone = {
  name: string;
  timestamp: string;
  dream_excerpt?: string;
};

type Goal = {
  name: string;
  description?: string;
  reward?: number;
  completed_at?: string | null;
  status?: string;
};

type Strategy = {
  id: string;
  goal: string;
  action: string;
  priority: number;
};

type LearnedSkill = {
  title: string;
  tags: string[];
  status: string;
  learned_on: string;
};

type TerminalPayload = {
  analysisText: string;
  visualPayload: {
    products?: any[];
    chartData?: ChartPoint[];
  };
};

const COMMAND_TABS = ["Sales", "Marketing", "Operations", "Shipments", "Financials", "Clients"];

export default function AIONDashboard() {
  useAuthRedirect("supplier");

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

  // Supplier Metrics
  const [metrics, setMetrics] = useState<SupplierMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Split Pane
  const containerRef = useRef<HTMLDivElement>(null);
  const [dividerX, setDividerX] = useState(0);
  const dragging = useRef(false);

  useLayoutEffect(() => {
    const w = containerRef.current?.clientWidth ?? 0;
    setDividerX(w / 2);
  }, []);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current || !containerRef.current) return;
      const { left, width } = containerRef.current.getBoundingClientRect();
      let x = e.clientX - left;
      const min = width * 0.2,
        max = width * 0.8;
      x = Math.max(min, Math.min(max, x));
      setDividerX(x);
    };
    const onUp = () => {
      dragging.current = false;
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, []);

  const onDividerDown = (e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;
  };

  // Terminal
  const [queryText, setQueryText] = useState("");
  const [analysisText, setAnalysis] = useState("");
  const [chartData, setChartData] = useState<ChartPoint[] | null>(null);
  const [searchResults, setResults] = useState<any[] | null>(null);
  const [working, setWorking] = useState(false);

  const sendQuery = async () => {
    if (!queryText.trim()) return;
    setWorking(true);
    setAnalysis("");
    setResults(null);
    setChartData(null);

    try {
      const resp = await fetch(`${API_BASE}/terminal/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ prompt: queryText.trim() }),
      });
      if (!resp.ok) throw new Error(`Status ${resp.status}`);
      const json = (await resp.json()) as TerminalPayload;
      setAnalysis(json.analysisText || "");
      if (Array.isArray(json.visualPayload.products)) {
        setResults(json.visualPayload.products);
      } else if (Array.isArray(json.visualPayload.chartData)) {
        setChartData(json.visualPayload.chartData);
      }
    } catch {
      setAnalysis("❌ Something went wrong.");
    } finally {
      setWorking(false);
    }
  };

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendQuery();
    }
  };
  const onTabClick = (label: string) => {
    setQueryText(label);
    setTimeout(sendQuery, 50);
  };

  // Fetch supplier metrics
  useEffect(() => {
    let active = true;
    fetch("/api/supplier/dashboard")
      .then((r) => r.json())
      .then((data: SupplierMetrics) => active && setMetrics(data))
      .catch((err) => active && setError(err.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  const totalW = containerRef.current?.clientWidth ?? 0;
  const rightWidth = Math.max(0, totalW - dividerX);

  if (loading)
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <p>Loading…</p>
      </div>
    );
  if (error || !metrics)
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <p className="text-red-500">{error || "Error loading metrics"}</p>
      </div>
    );

  return (
    <div className="relative flex flex-col h-screen bg-gray-50">
      {/* Split Panes */}
      <div ref={containerRef} className="relative flex-1 flex overflow-hidden min-h-0">
        {/* Left Pane */}
        <div className="bg-white p-6 overflow-auto min-w-0" style={{ flexBasis: dividerX }}>
          <h2 className="text-xl font-semibold mb-4">Hello, Supplier — welcome.</h2>
          <p>
            Sales Today: <span className="text-blue-600">{metrics.totalSalesToday}</span>
          </p>
          <p>
            Active Listings: <span className="text-green-600">{metrics.activeListings}</span>
          </p>
          <p>
            Open Orders: <span className="text-green-600">{metrics.openOrders}</span>
          </p>
          <p>
            30d Proceeds: <span className="text-blue-600">£{metrics.proceeds30d}</span>
          </p>
          <p>
            Feedback: <span className="text-purple-600">{metrics.feedbackRating}</span>
          </p>
          {analysisText && (
            <div className="mt-6 space-y-1">
              {analysisText.split("\n").map((l, i) => (
                <p key={i}>{l}</p>
              ))}
            </div>
          )}
        </div>

        {/* Draggable Divider */}
        <div
          onMouseDown={onDividerDown}
          className="absolute top-0 h-full w-1 bg-gray-300 cursor-col-resize z-20"
          style={{ left: dividerX - 0.5 }}
        />

        {/* Right Pane */}
        <div className="bg-white p-6 overflow-auto min-w-0" style={{ flexBasis: rightWidth }}>
          {searchResults ? (
            searchResults.map((item, i) => (
              <div
                key={i}
                className="bg-white border border-gray-200 rounded p-4 mb-4 shadow-sm"
              >
                <pre className="text-xs">{JSON.stringify(item, null, 2)}</pre>
              </div>
            ))
          ) : chartData?.length ? (
            <Chart data={chartData} height={(containerRef.current?.clientHeight ?? 0) - 64} />
          ) : (
            <div className="h-full flex items-center justify-center text-gray-500">
              <p>Select a tab or ask a question to see visual output here.</p>
            </div>
          )}
        </div>
      </div>

      {/* Sticky Footer */}
      <footer className="sticky bottom-0 left-0 w-full bg-white border-t border-gray-200 px-6 py-3 flex items-center space-x-3">
        <input
          type="text"
          className="flex-1 border border-gray-300 rounded px-4 py-2"
          placeholder="Type a question…"
          value={queryText}
          onChange={(e) => setQueryText(e.target.value)}
          onKeyDown={onKey}
        />
        <button
          onClick={sendQuery}
          disabled={working}
          className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          {working ? "Working…" : "Send"}
        </button>
        <div className="flex space-x-2">
          {COMMAND_TABS.map((label) => (
            <button
              key={label}
              onClick={() => onTabClick(label)}
              className="px-3 py-1 border rounded text-sm"
            >
              {label}
            </button>
          ))}
        </div>
      </footer>
    </div>
  );
}
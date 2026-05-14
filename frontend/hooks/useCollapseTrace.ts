import { useEffect, useState } from "react";

interface GlyphType {
  glyph_id: string;
  symbol: string;
  timestamp: string;
  cost?: number;
  entangled?: string[];
  collapse_trace?: boolean;
  modulation_strategy?: string;
  coherence_score?: number;
  tick?: number;
  collapse_state?: string;
}

interface CollapseTraceResponse {
  ticks: number[];
  grouped_beams: Record<number, GlyphType[]>;
  all_beams: GlyphType[];
}

export default function useCollapseTrace(showCollapsed: boolean) {
  const [data, setData] = useState<CollapseTraceResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const signal = controller.signal;

    const fetchTrace = async () => {
      setLoading(true);
      setError(null);

      try {
        const res = await fetch(
          `/api/collapse_traces/recent?show_collapsed=${showCollapsed}`,
          { signal }
        );

        if (!res.ok) {
          throw new Error(`Failed to fetch collapse traces: ${res.statusText}`);
        }

        const json = await res.json();

        if (
          json &&
          Array.isArray(json.ticks) &&
          typeof json.grouped_beams === "object" &&
          Array.isArray(json.all_beams)
        ) {
          setData(json);
        } else {
          throw new Error("Malformed collapse trace response");
        }
      } catch (err: any) {
        if (err.name !== "AbortError") {
          console.error("Collapse trace fetch error:", err);
          setError(err.message || "Unknown error");
          setData(null);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchTrace();

    return () => {
      controller.abort();
    };
  }, [showCollapsed]);

  return { data, loading, error };
}
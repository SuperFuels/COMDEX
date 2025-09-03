import { useEffect, useState } from "react";
import useWebSocket from "@/hooks/useWebSocket";

export function useCollapseMetrics() {
  const [collapseHistory, setCollapseHistory] = useState<number[]>([]);
  const [decoherenceHistory, setDecoherenceHistory] = useState<number[]>([]);
  const [latestCollapse, setLatestCollapse] = useState<number | null>(null);
  const [latestDecoherence, setLatestDecoherence] = useState<number | null>(null);

  useWebSocket(
    "/ws/ghx", // adjust if your collapse metrics are from another channel
    (data) => {
      if (data?.type === "collapse_metrics") {
        const collapse = data.collapse_per_sec ?? null;
        const decoherence = data.decoherence_rate ?? null;

        if (collapse !== null) {
          setLatestCollapse(collapse);
          setCollapseHistory((prev) => [...prev.slice(-49), collapse]);
        }

        if (decoherence !== null) {
          setLatestDecoherence(decoherence);
          setDecoherenceHistory((prev) => [...prev.slice(-49), decoherence]);
        }
      }
    },
    ["collapse_metrics"]
  );

  return {
    collapseHistory,
    decoherenceHistory,
    latestCollapse,
    latestDecoherence,
  };
}
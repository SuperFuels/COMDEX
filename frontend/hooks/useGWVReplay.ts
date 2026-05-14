// File: frontend/hooks/useGWVReplay.ts

import { useEffect, useState } from "react";

type GWVTrace = {
  timestamp: number;
  collapse: number;
  decoherence: number;
};

export function useGWVReplay(containerId: string) {
  const [traceData, setTraceData] = useState<GWVTrace[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchTrace() {
      try {
        const res = await fetch(`/api/gwv_trace?container_id=${containerId}`);
        const data = await res.json();
        setTraceData(data.entries || []);
      } catch (e) {
        console.warn("Failed to load GWV trace:", e);
        setTraceData([]);
      } finally {
        setIsLoading(false);
      }
    }
    fetchTrace();
  }, [containerId]);

  return { traceData, isLoading };
}
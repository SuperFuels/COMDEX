// frontend/hooks/useWaveTelemetry.ts
import { useEffect, useMemo, useState } from "react";
import useWebSocket from "@/hooks/useWebSocket";

export type SNRStatus = "ok" | "low" | "unknown";

export function useWaveTelemetry(containerId: string): {
  latestCollapse: number | null;
  latestDecoherence: number | null;
  collapseHistory: number[];
  decoherenceHistory: number[];
  snrStatus: SNRStatus;
} {
  const [latestCollapse, setLatestCollapse] = useState<number | null>(null);
  const [latestDecoherence, setLatestDecoherence] = useState<number | null>(null);
  const [collapseHistory, setCollapseHistory] = useState<number[]>([]);
  const [decoherenceHistory, setDecoherenceHistory] = useState<number[]>([]);
  const [snrStatus, setSnrStatus] = useState<SNRStatus>("unknown");

  // Memoize the handler so the WebSocket hook isn't reinitialized on every render
  const handleMessage = useMemo(
    () => (raw: unknown) => {
      let msg: any = raw;

      // If the ws lib delivers strings, try JSON.parse; otherwise use as-is
      if (typeof raw === "string") {
        try {
          msg = JSON.parse(raw);
        } catch {
          // Not JSON — bail out quietly
          return;
        }
      }

      switch (msg?.type) {
        case "collapse_rate": {
          const val = typeof msg.value === "number" ? msg.value : Number(msg.value);
          if (!Number.isNaN(val)) {
            setLatestCollapse(val);
            setCollapseHistory((h) => [...h.slice(-199), val]);
          }
          break;
        }
        case "decoherence": {
          const val = typeof msg.value === "number" ? msg.value : Number(msg.value);
          if (!Number.isNaN(val)) {
            setLatestDecoherence(val);
            setDecoherenceHistory((h) => [...h.slice(-199), val]);
          }
          break;
        }
        case "snr_status": {
          setSnrStatus(msg.status === "low" ? "low" : "ok");
          break;
        }
        default:
          // ignore anything else
          break;
      }
    },
    []
  );

  // Your useWebSocket expects (path, onMessage, [options?])
  // We don’t need anything from the return value here.
  useWebSocket(`/ws/wavescope/${containerId}`, handleMessage);

  // If containerId changes, you may want to clear histories
  useEffect(() => {
    setLatestCollapse(null);
    setLatestDecoherence(null);
    setCollapseHistory([]);
    setDecoherenceHistory([]);
    setSnrStatus("unknown");
  }, [containerId]);

  return { latestCollapse, latestDecoherence, collapseHistory, decoherenceHistory, snrStatus };
}
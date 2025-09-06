import { useEffect, useState } from "react";
import { useWebSocket } from "@/lib/websocket";  // adjust for your setup

export function useWaveTelemetry() {
  const [metrics, setMetrics] = useState<any[]>([]);
  const ws = useWebSocket();

  useEffect(() => {
    if (!ws) return;
    const handler = (data: any) => {
      if (data?.event?.startsWith("beam_")) {
        setMetrics((prev) => [...prev.slice(-99), data]);
      }
    };
    ws.on("beam_event", handler);
    return () => ws.off("beam_event", handler);
  }, [ws]);

  return { metrics };
}
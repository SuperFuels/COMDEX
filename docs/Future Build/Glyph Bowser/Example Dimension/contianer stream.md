2) frontend/hooks/useContainerStream.ts


// frontend/hooks/useContainerStream.ts
import { useEffect, useRef, useState } from "react";

export type ContainerEvent = {
  type: string;
  data?: any;
  meta?: any;
  ts?: number;
};

type Options = {
  mock?: boolean;
  intervalMs?: number;
  mockFn?: (t: number) => ContainerEvent;
};

/**
 * Connects to a container event stream (WS/SSE).
 * Falls back to a local mock if no backend stream is present.
 */
export default function useContainerStream(
  containerId: string,
  running = true,
  opts: Options = {}
) {
  const { mock = true, intervalMs = 200, mockFn } = opts;
  const [connected, setConnected] = useState(false);
  const [last, setLast] = useState<ContainerEvent | null>(null);
  const t0 = useRef<number>(Date.now());
  const wsRef = useRef<WebSocket | null>(null);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    let closed = false;

    // Try WebSocket first
    try {
      const ws = new WebSocket(
        `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/container/${encodeURIComponent(containerId)}`
      );
      wsRef.current = ws;

      ws.onopen = () => !closed && setConnected(true);
      ws.onclose = () => !closed && setConnected(false);
      ws.onerror = () => !closed && setConnected(false);
      ws.onmessage = (e) => {
        try {
          const ev: ContainerEvent = JSON.parse(e.data);
          setLast(ev);
        } catch {
          // ignore non-JSON messages
        }
      };
    } catch {
      // swallow
    }

    // Optional mock generator
    if (mock) {
      const loop = () => {
        if (!running) return;
        const t = Date.now() - t0.current;
        const ev =
          mockFn?.(t) ??
          ({
            type: "field_update",
            data: { E: Math.sin(t / 500), B: Math.cos(t / 700) },
          } as ContainerEvent);
        setLast(ev);
        // @ts-ignore
        timerRef.current = setTimeout(loop, intervalMs);
      };
      // @ts-ignore
      timerRef.current = setTimeout(loop, intervalMs);
    }

    return () => {
      closed = true;
      try {
        wsRef.current?.close();
      } catch {}
      if (timerRef.current) {
        clearTimeout(timerRef.current as any);
        timerRef.current = null;
      }
    };
  }, [containerId, intervalMs, mock, mockFn, running]);

  return { connected, last };
}



// frontend/components/SQS/LiveQpuCpuPanel.tsx
"use client";

import React, { useEffect, useState, useRef } from "react";

// Minimal in-file fallback for a websocket bridge so we don't depend on external modules.
class WebSocketBridge {
  private ws: WebSocket | null = null;
  private onMsgCb: ((msg: any) => void) | null = null;

  constructor(pathOrUrl: string) {
    if (typeof window === "undefined") return;

    const isAbsolute = /^wss?:\/\//i.test(pathOrUrl);
    const url = isAbsolute
      ? pathOrUrl
      : `${window.location.protocol === "https:" ? "wss" : "ws"}://${
          window.location.host
        }${pathOrUrl.startsWith("/") ? pathOrUrl : `/${pathOrUrl}`}`;

    try {
      this.ws = new WebSocket(url);
      this.ws.onmessage = (ev) => {
        let payload: any;
        try {
          payload = JSON.parse(ev.data);
        } catch {
          payload = ev.data;
        }
        this.onMsgCb?.(payload);
      };
      // noop handlers to avoid unhandled events
      this.ws.onerror = () => {};
      this.ws.onclose = () => {};
    } catch {
      // swallow constructor errors; caller can decide what to do
    }
  }

  onMessage(cb: (msg: any) => void) {
    this.onMsgCb = cb;
  }

  send(data: any) {
    try {
      this.ws?.send(typeof data === "string" ? data : JSON.stringify(data));
    } catch {
      /* noop */
    }
  }

  close() {
    try {
      this.ws?.close();
    } catch {
      /* noop */
    } finally {
      this.ws = null;
    }
  }
}

export interface CellMetrics {
  cell_id: string;
  sqi: number;
  mutation_count?: number;
  exec_time?: number;
  last_result?: any;
  source?: string;
}

interface LiveQpuCpuPanelProps {
  containerId: string;
}

export const LiveQpuCpuPanel: React.FC<LiveQpuCpuPanelProps> = ({ containerId }) => {
  const [cellMetrics, setCellMetrics] = useState<Map<string, CellMetrics>>(new Map());
  const [showCpu, setShowCpu] = useState(true);
  const wsRef = useRef<WebSocketBridge | null>(null);

  useEffect(() => {
    if (!containerId) return;
    const ws = new WebSocketBridge(`/api/qfc?container_id=${encodeURIComponent(containerId)}`);
    wsRef.current = ws;

    ws.onMessage((msg: any) => {
      const data = msg?.payload ?? msg; // support either {payload} or bare object
      if (!data || !data.cell_id) return;

      setCellMetrics((prev) => {
        const updated = new Map(prev);
        const existing = updated.get(data.cell_id) || {};
        updated.set(data.cell_id, { ...(existing as any), ...(data as any) });
        return updated;
      });
    });

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [containerId]);

  const metricsArray = Array.from(cellMetrics.values()).sort((a, b) =>
    a.cell_id.localeCompare(b.cell_id)
  );

  return (
    <div className="live-qpu-cpu-panel">
      <div className="panel-header">
        <h3>Live CPU / QPU Metrics</h3>
        <button onClick={() => setShowCpu((v) => !v)}>Show {showCpu ? "QPU" : "CPU"}</button>
      </div>

      <table className="metrics-table">
        <thead>
          <tr>
            <th>Cell ID</th>
            <th>{showCpu ? "CPU SQI" : "QPU SQI"}</th>
            <th>Mutation Count</th>
            <th>Exec Time (s)</th>
            <th>Last Result</th>
          </tr>
        </thead>
        <tbody>
          {metricsArray.map((cell) => (
            <tr key={cell.cell_id}>
              <td>{cell.cell_id}</td>
              <td>{typeof cell.sqi === "number" ? cell.sqi.toFixed(3) : "—"}</td>
              <td>{cell.mutation_count ?? "—"}</td>
              <td>{typeof cell.exec_time === "number" ? cell.exec_time.toFixed(6) : "—"}</td>
              <td>
                <pre style={{ maxWidth: 240, overflowX: "auto", margin: 0 }}>
                  {cell.last_result == null ? "—" : JSON.stringify(cell.last_result)}
                </pre>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <style jsx>{`
        .live-qpu-cpu-panel {
          padding: 10px;
          background: #1e1e2f;
          color: #fff;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono",
            "Courier New", monospace;
          max-height: 600px;
          overflow: auto;
          border: 1px solid #444;
          border-radius: 6px;
        }
        .panel-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
          gap: 8px;
        }
        .panel-header button {
          background: #2d2d42;
          color: #fff;
          border: 1px solid #52527a;
          padding: 4px 8px;
          border-radius: 4px;
          cursor: pointer;
        }
        table.metrics-table {
          width: 100%;
          border-collapse: collapse;
          table-layout: fixed;
        }
        table.metrics-table th,
        table.metrics-table td {
          border: 1px solid #555;
          padding: 6px 8px;
          text-align: left;
          vertical-align: top;
          word-break: break-word;
        }
        table.metrics-table th {
          background-color: #2e2e3f;
        }
        table.metrics-table td {
          background-color: #252533;
        }
      `}</style>
    </div>
  );
};
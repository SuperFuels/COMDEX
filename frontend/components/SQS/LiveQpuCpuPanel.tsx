import React, { useEffect, useState, useRef } from "react";
import { WebSocketBridge } from "../../utils/websocket_bridge"; // assumes you have a ws helper

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
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocketBridge(`/api/qfc?container_id=${containerId}`);
    wsRef.current = ws;

    ws.onMessage((msg: any) => {
      const data = msg?.payload;
      if (!data || !data.cell_id) return;

      setCellMetrics(prev => {
        const updated = new Map(prev);
        updated.set(data.cell_id, { ...updated.get(data.cell_id), ...data });
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
        <button onClick={() => setShowCpu(!showCpu)}>
          Show {showCpu ? "QPU" : "CPU"}
        </button>
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
          {metricsArray.map(cell => (
            <tr key={cell.cell_id}>
              <td>{cell.cell_id}</td>
              <td>{cell.sqi?.toFixed(3)}</td>
              <td>{cell.mutation_count ?? "-"}</td>
              <td>{cell.exec_time?.toFixed(6) ?? "-"}</td>
              <td>
                <pre style={{ maxWidth: 200, overflowX: "auto" }}>
                  {JSON.stringify(cell.last_result)}
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
          font-family: monospace;
          max-height: 600px;
          overflow: auto;
          border: 1px solid #444;
          border-radius: 4px;
        }
        .panel-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }
        table.metrics-table {
          width: 100%;
          border-collapse: collapse;
        }
        table.metrics-table th,
        table.metrics-table td {
          border: 1px solid #555;
          padding: 4px 6px;
          text-align: left;
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
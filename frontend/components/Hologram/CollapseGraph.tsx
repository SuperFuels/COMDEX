"use client";

import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from "recharts";
import { useCollapseMetrics } from "@/hooks/useCollapseMetrics";

type GraphPoint = {
  time: number;
  collapse: number;
  decoherence: number;
  coherence_delta?: number;
  coherence_trend?: string; // 📈 / 📉 / ➖
};

export default function CollapseGraph() {
  const { collapseHistory, decoherenceHistory } = useCollapseMetrics();
  const [data, setData] = useState<GraphPoint[]>([]);

  useEffect(() => {
    const maxLength = Math.min(collapseHistory.length, decoherenceHistory.length);
    const sliced: GraphPoint[] = [];

    for (let i = 0; i < maxLength; i++) {
      const deco = decoherenceHistory[i] * 100;
      const prev = decoherenceHistory[i - 1] ?? decoherenceHistory[i];
      const delta = prev - decoherenceHistory[i];
      let trend = "➖";

      if (Math.abs(delta) > 0.0001) {
        trend = delta > 0 ? "📈" : "📉";
      }

      sliced.push({
        time: i,
        collapse: collapseHistory[i],
        decoherence: deco,
        coherence_delta: delta * 100,
        coherence_trend: trend
      });
    }

    setData(sliced);
  }, [collapseHistory, decoherenceHistory]);

  return (
    <div className="mt-4 bg-black/80 p-4 rounded-xl border border-green-600 shadow">
      <h3 className="text-green-300 text-sm font-bold mb-2">
        📉 Collapse / Decoherence Graph
      </h3>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#333" />
          <XAxis dataKey="time" stroke="#aaa" />
          <YAxis stroke="#aaa" />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const point = payload[0].payload as GraphPoint;
                return (
                  <div className="bg-black text-white p-2 text-xs border border-gray-600 rounded">
                    <div>🕒 Time: {point.time}</div>
                    <div>⚡ Collapse/sec: {point.collapse.toFixed(2)}</div>
                    <div>☢️ Decoherence: {point.decoherence.toFixed(2)}%</div>
                    <div>
                      {point.coherence_trend} Coherence Delta:{" "}
                      {point.coherence_delta?.toFixed(3)}%
                    </div>
                  </div>
                );
              }
              return null;
            }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="collapse"
            stroke="#00FFAA"
            dot={false}
            name="Collapse/sec"
          />
          <Line
            type="monotone"
            dataKey="decoherence"
            stroke="#FF66CC"
            dot={false}
            name="Decoherence (%)"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
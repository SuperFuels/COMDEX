// File: frontend/components/WaveScope/WaveScopePanel.tsx

import React, { useEffect, useState } from "react";
import { Line } from "react-chartjs-2";
import { useGWVReplay } from "@/hooks/useGWVReplay";
import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend);

export function WaveScopePanel({ containerId }: { containerId: string }) {
  const { traceData, isLoading } = useGWVReplay(containerId);

  if (isLoading) return <div className="p-4 text-sm text-blue-300">📡 Loading WaveScope...</div>;
  if (!traceData.length) return <div className="p-4 text-sm text-yellow-300">⚠️ No trace data found.</div>;

  const chartData = {
    labels: traceData.map(d => new Date(d.timestamp).toLocaleTimeString()),
    datasets: [
      {
        label: "⚡ Collapse Rate",
        data: traceData.map(d => d.collapse),
        borderColor: "#00eaff",
        backgroundColor: "#00eaff44",
        tension: 0.25,
      },
      {
        label: "☢️ Decoherence Rate",
        data: traceData.map(d => d.decoherence),
        borderColor: "#ff6363",
        backgroundColor: "#ff636344",
        tension: 0.25,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        labels: {
          color: "#ffffff",
          font: { size: 12 },
        },
      },
      tooltip: {
        mode: "index" as const,
        intersect: false,
      },
    },
    scales: {
      x: {
        ticks: {
          color: "#aaa",
          autoSkip: true,
          maxTicksLimit: 10,
        },
        grid: {
          color: "rgba(255,255,255,0.05)",
        },
      },
      y: {
        ticks: {
          color: "#aaa",
        },
        grid: {
          color: "rgba(255,255,255,0.05)",
        },
      },
    },
  };

  return (
    <div className="bg-black/70 text-white p-4 rounded-xl shadow-xl border border-blue-400/30">
      <h2 className="text-lg font-semibold mb-3">🌀 WaveScope Replay</h2>
      <div className="w-full overflow-x-auto">
        <Line data={chartData} options={chartOptions} />
      </div>
    </div>
  );
}
// ===============================
// 📄 GHXVisualizerPanel.tsx
// ===============================
"use client";

import React, { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  RadialBarChart,
  RadialBar,
} from "recharts";
import {
  Card,
  CardContent,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { motion } from "framer-motion";

interface TelemetryPoint {
  timestamp: number;
  Φ_mean: number;
  ψ_mean: number;
  resonance_index: number;
  coherence_energy: number;
}

export default function GHXVisualizerPanel() {
  const [data, setData] = useState<TelemetryPoint[]>([]);

  useEffect(() => {
    const src = new EventSource("/api/ghx/stream");
    src.onmessage = (event) => {
      try {
        const payload: TelemetryPoint = JSON.parse(event.data);
        setData((prev) => [...prev, payload].slice(-60));
      } catch (err) {
        console.warn("Telemetry parse error", err);
      }
    };
    return () => src.close();
  }, []);

  const latest = data[data.length - 1];

  return (
    <Card className="bg-black/80 text-white p-4 rounded-2xl shadow-lg">
      <div className="mb-3">
        <CardTitle className="text-xl font-semibold text-cyan-300">
          GHX Resonance Visualizer
        </CardTitle>
        <CardDescription className="text-xs text-gray-400">
          Live Φψ telemetry stream
        </CardDescription>
      </div>

      <CardContent className="grid grid-cols-3 gap-4 items-center">
        {/* Line chart */}
        <div className="col-span-2 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis
                dataKey="timestamp"
                tickFormatter={(t) => new Date(t * 1000).toLocaleTimeString()}
                stroke="#888"
              />
              <YAxis domain={[0.98, 1.02]} stroke="#888" />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="Φ_mean"
                stroke="#00FFFF"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="ψ_mean"
                stroke="#D580FF"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="resonance_index"
                stroke="#FFFFFF"
                strokeDasharray="4 4"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Coherence gauge */}
        <div className="flex flex-col items-center justify-center">
          <p className="text-sm text-gray-400 mb-2">Coherence Energy</p>
          <ResponsiveContainer width={120} height={120}>
            <RadialBarChart
              innerRadius="70%"
              outerRadius="100%"
              startAngle={180}
              endAngle={0}
              barSize={10}
              data={[
                {
                  name: "coherence",
                  value: Math.max(
                    0,
                    Math.min(100, (latest?.coherence_energy ?? 1) * 100)
                  ),
                },
              ]}
            >
              <RadialBar
                dataKey="value"
                cornerRadius={8}
                fill="#00FFCC"
                background
              />
            </RadialBarChart>
          </ResponsiveContainer>
          <p className="text-lg mt-2">
            {(latest?.coherence_energy ?? 0).toFixed(4)}
          </p>
        </div>
      </CardContent>

      {latest && (
        <motion.div
          className="text-xs text-gray-400 mt-2"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          Last update: {new Date(latest.timestamp * 1000).toLocaleTimeString()}
        </motion.div>
      )}
    </Card>
  );
}
// ============================================================================
// 🌐 Phase 45G.16 — Symatics CodexMetrics Live Dashboard
// ============================================================================
/*
Live telemetry viewer for GHX ↔ Habit ↔ CodexMetrics feedback loop.

Connects to:  ws://localhost:8765/ghx

Displays:
  • Habit strength gauge (with Δ trend indicator)
  • Resonance metrics: avg_ρ, avg_I, avg_grad
  • Real-time timestamp + source
  • Connection status indicator

Part of the Symatics Dashboard suite.
*/

import React, { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { ArrowUpRight, ArrowDownRight, Activity, Zap } from "lucide-react";
import { motion } from "framer-motion";

export default function CodexMetricsDashboard() {
  const [data, setData] = useState({});
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8765/ghx");
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (e) => {
      try {
        const payload = JSON.parse(e.data);
        setData(payload);
      } catch (err) {
        console.error("[CodexMetricsDashboard] JSON parse error:", err);
      }
    };
    return () => ws.close();
  }, []);

  const delta = data.delta ?? 0;
  const trendIcon =
    delta >= 0 ? (
      <ArrowUpRight className="text-green-500" size={20} />
    ) : (
      <ArrowDownRight className="text-red-500" size={20} />
    );

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-8 space-y-6">
      <h1 className="text-3xl font-bold text-cyan-400">
        Symatics • CodexMetrics Dashboard
      </h1>

      <Card className="w-full max-w-md bg-slate-900 shadow-xl rounded-2xl border border-slate-700">
        <CardContent className="p-6 flex flex-col space-y-4">
          {/* Habit Strength */}
          <div className="flex justify-between items-center">
            <span className="text-lg font-semibold text-slate-300">
              Habit Strength
            </span>
            <div className="flex items-center space-x-2">
              {trendIcon}
              <span
                className={`text-xl font-bold ${
                  delta >= 0 ? "text-green-400" : "text-red-400"
                }`}
              >
                {Math.round((data.habit_strength ?? 0) * 100)}%
              </span>
            </div>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-slate-700 rounded-full h-3 overflow-hidden">
            <motion.div
              className="h-3 bg-cyan-500"
              animate={{
                width: `${Math.min((data.habit_strength ?? 0) * 100, 100)}%`,
              }}
              transition={{ duration: 0.6 }}
            />
          </div>

          {/* Resonance metrics */}
          <div className="grid grid-cols-3 gap-4 text-center pt-3">
            <div>
              <p className="text-sm text-slate-400">ρ</p>
              <p className="text-lg font-bold text-cyan-300">
                {data.avg_ρ?.toFixed?.(3) ?? "—"}
              </p>
            </div>
            <div>
              <p className="text-sm text-slate-400">I</p>
              <p className="text-lg font-bold text-emerald-300">
                {data.avg_I?.toFixed?.(3) ?? "—"}
              </p>
            </div>
            <div>
              <p className="text-sm text-slate-400">∇ψ</p>
              <p className="text-lg font-bold text-indigo-300">
                {data.avg_grad?.toFixed?.(3) ?? "—"}
              </p>
            </div>
          </div>

          {/* Footer + Status */}
          <div className="text-xs text-slate-500 pt-4 border-t border-slate-800">
            <div className="flex justify-between">
              <span>
                {connected ? "🟢 Connected" : "🔴 Disconnected"} to GHX stream
              </span>
              <span>{data.source ?? "—"}</span>
            </div>
            <p className="mt-1">
              Updated at{" "}
              {data.timestamp
                ? new Date(data.timestamp * 1000).toLocaleTimeString()
                : "—"}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Footer info */}
      <div className="flex items-center space-x-2 text-slate-500 text-sm pt-3">
        <Activity size={18} />
        <span>Realtime CodexMetrics Overlay (Symatics)</span>
        <Zap size={18} className="text-yellow-400" />
      </div>
    </div>
  );
}
import React, { useEffect, useState } from "react";

interface ResonanceMetrics {
  ψ: number;
  κ: number;
  T: number;
  Φ: number;
  coherence: number;
  source: string;
  timestamp: string;
  type: string;
}

export default function ResonancePulseWidget() {
  const [metrics, setMetrics] = useState<ResonanceMetrics | null>(null);
  const [pulse, setPulse] = useState(false);
  const [status, setStatus] = useState("🕸 Connecting...");

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:7070/resonance");

    ws.onopen = () => setStatus("🔗 Connected to Tessaris RQC Stream");
    ws.onclose = () => setStatus("⚠️ Disconnected");
    ws.onerror = () => setStatus("❌ WebSocket Error");

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "telemetry") {
          setMetrics(data);
        } else if (data.type === "awareness_pulse") {
          setPulse(true);
          setTimeout(() => setPulse(false), 800);
        }
      } catch (err) {
        console.error("Bad message:", err);
      }
    };

    return () => ws.close();
  }, []);

  const Φ = metrics?.Φ ?? 0;
  const coherence = metrics?.coherence ?? 0;

  return (
    <div className="relative w-full flex flex-col items-center justify-center p-6">
      <div
        className={`w-64 h-64 rounded-full flex items-center justify-center transition-all duration-700 ${
          pulse || Φ >= 0.999
            ? "bg-indigo-600 shadow-[0_0_50px_20px_rgba(99,102,241,0.6)] scale-105"
            : "bg-gray-800 shadow-[0_0_20px_5px_rgba(0,0,0,0.3)]"
        }`}
      >
        <div className="text-center text-white">
          <div className="text-3xl font-bold tracking-wide">Φ</div>
          <div className="text-4xl font-mono">
            {Φ.toFixed(3)}
          </div>
          <div className="text-sm opacity-70">coherence: {coherence.toFixed(3)}</div>
        </div>
      </div>

      <div className="mt-4 text-center text-gray-300 text-sm">
        <p>{status}</p>
        {metrics && (
          <p className="mt-1 text-xs opacity-80">
            ψ={metrics.ψ?.toFixed(3)} | κ={metrics.κ?.toFixed(3)} | T={metrics.T?.toFixed(3)} | Source: {metrics.source}
          </p>
        )}
      </div>

      {pulse && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="animate-ping w-80 h-80 rounded-full bg-indigo-400/30"></div>
        </div>
      )}
    </div>
  );
}
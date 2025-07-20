// frontend/components/aion/GlyphSummaryHUD.tsx

import React, { useEffect, useState } from "react";

interface GlyphSummary {
  total: number;
  types: Record<string, number>;
  changed: number;
  decayed: number;
  lifespanStats: {
    average: number;
    oldest: number;
    youngest: number;
  };
}

interface GlyphDiff {
  changed: number;
  decayed: number;
  summary: GlyphSummary;
}

interface AvatarRuntimeSummary {
  tick: number;
  mode: string;
  position: {
    x: number;
    y: number;
    z: number;
    t: number;
  };
  container: string;
  active_glyphs?: number;
}

interface GlyphTrigger {
  glyph: string;
  action: string;
  tick: number;
  role?: string;
}

interface GlyphSummaryHUDProps {
  glyphDiff?: GlyphDiff;
}

const GlyphSummaryHUD: React.FC<GlyphSummaryHUDProps> = ({ glyphDiff }) => {
  const [summary, setSummary] = useState<GlyphSummary | null>(null);
  const [runtime, setRuntime] = useState<AvatarRuntimeSummary | null>(null);
  const [trigger, setTrigger] = useState<GlyphTrigger | null>(null);
  const [traceLog, setTraceLog] = useState<GlyphTrigger[]>([]);

  useEffect(() => {
    if (glyphDiff?.summary) {
      setSummary(glyphDiff.summary);
    }
  }, [glyphDiff]);

  useEffect(() => {
    if (glyphDiff) return;

    const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/api\/?$/, "");
    const wsProtocol =
      typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsBase = API_BASE.replace(/^http/, wsProtocol).replace(/\/api\/?$/, '');
    const ws = new WebSocket(`${wsBase}/ws/updates`);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "glyph_summary") {
          setSummary(data.data);
        } else if (data.type === "glyph_trigger") {
          const newTrigger: GlyphTrigger = {
            glyph: data.glyph,
            action: data.action || "Unknown",
            tick: data.tick || 0,
            role: data.role,
          };
          setTrigger(newTrigger);
          setTraceLog((prev) => [newTrigger, ...prev.slice(0, 9)]);
        }
      } catch (err) {
        console.error("GlyphSummary WS error:", err);
      }
    };

    return () => {
      ws.close();
    };
  }, [glyphDiff]);

  useEffect(() => {
    const fetchRuntime = async () => {
      try {
        const res = await fetch("/avatar/runtime_tick_summary");
        const data = await res.json();
        setRuntime(data);
      } catch (e) {
        console.warn("Failed to fetch runtime summary", e);
      }
    };

    fetchRuntime();
    const interval = setInterval(fetchRuntime, 3000);
    return () => clearInterval(interval);
  }, []);

  if (!summary) {
    return <div className="text-sm text-gray-500">No glyph summary available.</div>;
  }

  return (
    <div className="p-4 rounded-md bg-white shadow border text-sm space-y-3 max-h-[90vh] overflow-y-auto">
      <div>🧮 <strong>Total Glyphs:</strong> {summary.total}</div>
      <div>🔠 <strong>Types:</strong>
        <ul className="ml-4 list-disc">
          {Object.entries(summary.types).map(([type, count]) => (
            <li key={type}>{type}: {count}</li>
          ))}
        </ul>
      </div>
      <div>🔁 <strong>Changed this tick:</strong> {summary.changed}</div>
      <div>💀 <strong>Decayed:</strong> {summary.decayed}</div>
      <div>📊 <strong>Lifespan:</strong>
        <ul className="ml-4 list-disc">
          <li>Average: {summary.lifespanStats.average.toFixed(2)}</li>
          <li>Oldest: {summary.lifespanStats.oldest}</li>
          <li>Youngest: {summary.lifespanStats.youngest}</li>
        </ul>
      </div>

      {runtime && (
        <div className="border-t pt-2">
          <div>🧠 <strong>Tick:</strong> {runtime.tick}</div>
          <div>🚦 <strong>Mode:</strong> {runtime.mode}</div>
          <div>📦 <strong>Container:</strong> {runtime.container}</div>
          <div>📍 <strong>Position:</strong> x={runtime.position.x}, y={runtime.position.y}, z={runtime.position.z}, t={runtime.position.t}</div>
          {runtime.active_glyphs !== undefined && (
            <div>✨ <strong>Active Glyphs:</strong> {runtime.active_glyphs}</div>
          )}
        </div>
      )}

      {trigger && (
        <div className="border-t pt-2">
          <div>⚡ <strong>Last Trigger:</strong> {trigger.glyph}</div>
          <div>🎬 <strong>Action:</strong> {trigger.role || trigger.action}</div>
          <div>⏱️ <strong>Tick:</strong> {trigger.tick}</div>
        </div>
      )}

      {traceLog.length > 0 && (
        <div className="border-t pt-2">
          <div>📜 <strong>Recent Glyph Triggers:</strong></div>
          <ul className="ml-4 mt-1 list-disc max-h-40 overflow-y-auto text-xs space-y-1">
            {traceLog.map((t, i) => (
              <li key={`${t.glyph}-${t.tick}-${i}`}>
                {t.tick}: <code>{t.glyph}</code> → <em>{t.role || t.action}</em>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default GlyphSummaryHUD;
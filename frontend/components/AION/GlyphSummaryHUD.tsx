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

interface GlyphSummaryHUDProps {
  glyphDiff?: GlyphDiff;
}

const GlyphSummaryHUD: React.FC<GlyphSummaryHUDProps> = ({ glyphDiff }) => {
  const [summary, setSummary] = useState<GlyphSummary | null>(null);

  useEffect(() => {
    if (glyphDiff?.summary) {
      setSummary(glyphDiff.summary);
    }
  }, [glyphDiff]);

  useEffect(() => {
    if (glyphDiff) return; // Skip WS if glyphDiff is provided

    const ws = new WebSocket("wss://comdex-api-kappa.vercel.app/ws/updates");

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "glyph_summary") {
          setSummary(data.data);
        }
      } catch (err) {
        console.error("GlyphSummary parse error:", err);
      }
    };

    ws.onerror = (e) => console.warn("GlyphSummary WS error:", e);
    ws.onclose = () => console.log("GlyphSummary WS closed");

    return () => ws.close();
  }, [glyphDiff]);

  if (!summary) {
    return <div className="text-sm text-gray-500">No glyph summary available.</div>;
  }

  return (
    <div className="p-4 rounded-md bg-white shadow border text-sm space-y-2">
      <div>🧮 Total Glyphs: <strong>{summary.total}</strong></div>
      <div>🔠 Types:
        <ul className="ml-4 list-disc">
          {Object.entries(summary.types).map(([type, count]) => (
            <li key={type}>{type}: {count}</li>
          ))}
        </ul>
      </div>
      <div>🔁 Changed this tick: <strong>{summary.changed}</strong></div>
      <div>💀 Decayed: <strong>{summary.decayed}</strong></div>
      <div>📊 Lifespan:
        <ul className="ml-4 list-disc">
          <li>Average: {summary.lifespanStats.average.toFixed(2)}</li>
          <li>Oldest: {summary.lifespanStats.oldest}</li>
          <li>Youngest: {summary.lifespanStats.youngest}</li>
        </ul>
      </div>
    </div>
  );
};

export default GlyphSummaryHUD;
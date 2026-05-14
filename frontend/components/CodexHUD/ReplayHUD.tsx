// components/CodexHUD/ReplayHUD.tsx
import React from "react";

export interface LatestTrace {
  glyph: string;
  action: string;
  timestamp: number; // 🔁 changed from string to number
  sqi?: boolean;
  replay_trace?: boolean;
  entangled_identity?: string;
  trigger_type?: string;
  cost?: number;
}

interface ReplayHUDProps {
  latestTrace: LatestTrace | null;
}

export const ReplayHUD: React.FC<ReplayHUDProps> = ({ latestTrace }) => {
  if (!latestTrace) return null;

  return (
    <div className="fixed top-16 right-2 w-[320px] bg-gray-900 border border-purple-800 p-3 rounded-lg shadow-lg z-50 text-sm">
      <div className="font-bold text-purple-300 mb-1">🌌 Latest Glyph</div>
      <div className="font-mono text-white whitespace-pre-wrap">
        ⟦ {latestTrace.glyph} ⟧ →{" "}
        <span className="text-green-400">{latestTrace.action}</span>
      </div>
      <div className="text-xs text-gray-400 mt-1">
        {new Date(latestTrace.timestamp).toLocaleString()}
      </div>

      <div className="flex flex-wrap gap-1 mt-2">
        {latestTrace.sqi && <span className="px-2 py-0.5 border border-purple-500 rounded text-purple-300 text-xs">🌌 SQI</span>}
        {latestTrace.replay_trace && <span className="px-2 py-0.5 border border-blue-400 rounded text-blue-300 text-xs">🛰️ Replay</span>}
        {latestTrace.entangled_identity && (
          <span className="px-2 py-0.5 border border-pink-400 rounded text-pink-300 text-xs">↔ Identity Link</span>
        )}
        {latestTrace.trigger_type && (
          <span className="px-2 py-0.5 border border-gray-500 rounded text-gray-300 text-xs">
            🕒 {latestTrace.trigger_type}
          </span>
        )}
        {latestTrace.cost !== undefined && (
          <span className="px-2 py-0.5 border border-red-600 bg-red-800 text-white rounded text-xs">
            💰 Cost: {latestTrace.cost.toFixed(2)}
          </span>
        )}
      </div>
    </div>
  );
};
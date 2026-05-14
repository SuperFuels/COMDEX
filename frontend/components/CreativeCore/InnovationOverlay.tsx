// InnovationOverlay.tsx

import React, { useEffect, useState } from "react";

type InnovationEntry = {
  wave_id: string;
  parent_wave_id?: string;
  score: number;
  glow: number;
  pulse: number;
  cause: string;
  timestamp: string;
};

export const InnovationOverlay: React.FC = () => {
  const [recentInnovations, setRecentInnovations] = useState<InnovationEntry[]>([]);

  useEffect(() => {
    const fetchRecent = async () => {
      try {
        const res = await fetch("/api/innovation_memory/recent");
        const data = await res.json();
        setRecentInnovations(data.entries || []);
      } catch (err) {
        console.error("[InnovationOverlay] Failed to load recent innovations:", err);
      }
    };

    fetchRecent();
    const interval = setInterval(fetchRecent, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="absolute top-4 right-4 bg-black/70 p-3 rounded-xl shadow-xl max-w-sm z-50 text-white text-sm">
      <h3 className="font-bold text-lg mb-2 text-emerald-400">🧠 Innovation Timeline</h3>
      {recentInnovations.length === 0 && <div className="text-gray-300">No recent forks.</div>}
      <ul className="space-y-1 max-h-64 overflow-y-auto">
        {recentInnovations.map((entry) => (
          <li key={entry.wave_id} className="border-b border-white/10 pb-1 mb-1">
            <div className="flex justify-between items-center">
              <span className="font-mono text-xs truncate w-36">{entry.wave_id}</span>
              <span className="text-emerald-300 font-bold">{entry.score.toFixed(2)}</span>
            </div>
            <div className="text-xs text-gray-300">
              {entry.cause} • glow: {entry.glow}, pulse: {entry.pulse}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};
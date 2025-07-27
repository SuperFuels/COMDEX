import React from "react";

export interface ReplayItem {
  glyph: string;
  content: string;
  timestamp: number;
}

interface ReplayListPanelProps {
  replays: ReplayItem[];
  onReplayClick: (replay: ReplayItem) => void;
}

export const ReplayListPanel: React.FC<ReplayListPanelProps> = ({
  replays,
  onReplayClick,
}) => {
  return (
    <div className="absolute right-4 top-20 w-[260px] max-h-[300px] overflow-y-auto bg-gray-900 border border-gray-700 rounded-lg shadow-lg p-3 z-20 text-sm text-white">
      <div className="font-bold text-purple-300 mb-2">🎞️ Replay History</div>
      {replays.length === 0 && (
        <div className="text-gray-400 italic">No glyphs replayed yet.</div>
      )}
      {replays.map((r, idx) => (
        <div
          key={idx}
          className="cursor-pointer hover:bg-gray-700/50 border-b border-gray-800 py-1 px-2 rounded"
          onClick={() => onReplayClick(r)}
        >
          <div className="text-white font-mono">⟦ {r.glyph} ⟧</div>
          <div className="text-green-400">{r.content}</div>
          <div className="text-xs text-gray-400">
            {new Date(r.timestamp).toLocaleString()}
          </div>
        </div>
      ))}
    </div>
  );
};
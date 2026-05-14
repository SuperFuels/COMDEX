// 📁 frontend/components/Codex/CodexScrollHistory.tsx

import React, { useEffect, useState } from "react";
import axios from "axios";

interface ScrollMemoryEntry {
  timestamp?: string;
  scroll: string;
  result: any;
  context: any;
}

export default function CodexScrollHistory() {
  const [history, setHistory] = useState<ScrollMemoryEntry[]>([]);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const res = await axios.get("/api/memory/trace?label=codex_scroll_execution&limit=10");
      if (res.data.status === "ok") {
        setHistory(res.data.results || []);
      }
    } catch (err) {
      console.error("Failed to fetch scroll history", err);
    }
  };

  return (
    <div className="bg-gray-900 p-4 rounded-lg text-white mt-4">
      <h3 className="font-bold text-cyan-400 mb-2">🧾 Codex Scroll History</h3>
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {history.map((entry, idx) => (
          <div key={idx} className="border border-cyan-700 p-3 rounded-lg">
            <div className="text-sm text-gray-400 mb-1">{entry.timestamp || "⏱ Recent"}</div>
            <div className="text-cyan-300 font-mono whitespace-pre-wrap mb-2">
              {entry.scroll}
            </div>
            <div className="text-green-400 text-sm">Result: {JSON.stringify(entry.result)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
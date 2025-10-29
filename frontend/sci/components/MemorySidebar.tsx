import React, { useEffect, useState } from "react";
import { SCIMemoryAPI } from "../api/sci_memory";

export default function MemorySidebar({ userId }: { userId: string }) {
  const [scrolls, setScrolls] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  async function loadScrolls() {
    setLoading(true);
    try {
      const data = await SCIMemoryAPI.list(userId);
      setScrolls(data);
    } catch (e) {
      console.error("❌ Failed to load scrolls", e);
    } finally {
      setLoading(false);
    }
  }

  async function handleReplay(scrollId: string) {
    try {
      await SCIMemoryAPI.replay(userId, scrollId);
      console.log(`🎬 Replayed scroll: ${scrollId}`);
    } catch (e) {
      console.error("Replay error:", e);
    }
  }

  useEffect(() => { loadScrolls(); }, [userId]);

  return (
    <div className="p-4 text-sm bg-zinc-900 text-white border-l border-zinc-800 h-full">
      <h2 className="font-semibold mb-3 text-lg">🧠 Memory Scrolls</h2>
      {loading ? (
        <div>Loading...</div>
      ) : (
        <ul className="space-y-2">
          {scrolls.map((s) => (
            <li key={s.id} className="flex justify-between items-center hover:bg-zinc-800 p-2 rounded">
              <span>{s.label || s.id}</span>
              <button
                onClick={() => handleReplay(s.id)}
                className="text-xs px-2 py-1 bg-blue-600 rounded hover:bg-blue-500"
              >
                ▶ Replay
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
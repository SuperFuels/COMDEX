// =====================================================
//  🧠 SCI Memory Panel — Resonant Scroll Browser
// =====================================================
"use client";

import React, { useEffect, useState } from "react";
import { SCIMemoryAPI } from "@/sci/api/sci_memory";

export default function SciMemoryPanel({
  wsUrl,
  containerId,
  userId = "default",
}: {
  wsUrl?: string;
  containerId?: string;
  userId?: string;
}) {
  const [scrolls, setScrolls] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [replaying, setReplaying] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function fetchScrolls() {
    setLoading(true);
    setError(null);
    try {
      const data = await SCIMemoryAPI.list(userId);
      setScrolls(data || []);
    } catch (e: any) {
      setError(e.message || "Failed to load memory scrolls");
    } finally {
      setLoading(false);
    }
  }

  async function replayScroll(id: string) {
    setReplaying(id);
    setMessage(null);
    try {
      await SCIMemoryAPI.replay(userId, id, containerId);
      setMessage(`✅ Replayed scroll '${id}' into QFC`);
    } catch (e: any) {
      setMessage(`❌ Replay error: ${e.message}`);
    } finally {
      setReplaying(null);
    }
  }

  useEffect(() => {
    fetchScrolls();
  }, [userId]);

  return (
    <div className="p-6 text-zinc-100 flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">🧠 Resonant Memory Browser</h2>
        <button
          onClick={fetchScrolls}
          disabled={loading}
          className="px-3 py-1 rounded border border-neutral-700 bg-neutral-800 hover:bg-neutral-700 text-sm"
        >
          {loading ? "Loading..." : "↻ Refresh"}
        </button>
      </div>

      {error && (
        <div className="text-red-400 text-sm mb-3 bg-red-500/10 border border-red-500/30 rounded p-2">
          {error}
        </div>
      )}
      {message && (
        <div className="text-xs text-green-300 mb-3 bg-green-500/10 border border-green-500/20 rounded p-2">
          {message}
        </div>
      )}

      <div className="flex-1 overflow-y-auto space-y-2 border border-neutral-800 rounded-lg p-2 bg-neutral-900/60">
        {scrolls.length === 0 && !loading && (
          <div className="text-zinc-500 text-sm text-center py-6">
            No memory scrolls found.
          </div>
        )}

        {scrolls.map((s) => (
          <div
            key={s.id || s.label}
            className="flex justify-between items-center p-2 border border-neutral-800 rounded bg-neutral-800/60 hover:bg-neutral-700/60 transition"
          >
            <div>
              <div className="font-mono text-sm text-zinc-200">
                {s.label || s.id}
              </div>
              <div className="text-xs text-zinc-400">
                {s.timestamp
                  ? new Date(s.timestamp * 1000).toLocaleString()
                  : "—"}
              </div>
            </div>
            <button
              onClick={() => replayScroll(s.id || s.label)}
              disabled={replaying === (s.id || s.label)}
              className="px-2 py-1 rounded border border-neutral-600 bg-neutral-700 hover:bg-neutral-600 text-xs"
            >
              {replaying === (s.id || s.label)
                ? "⟳ Replaying..."
                : "▶ Replay"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
import { useState, useEffect } from "react";

export interface ReplayItem {
  glyph: string;
  content: string;
  timestamp: number;
}

export interface LatestTrace {
  glyph: string;
  action: string;
  timestamp: number;
  sqi?: boolean;
  replay_trace?: boolean;
  entangled_identity?: string;
  trigger_type?: string;
  cost?: number;
}

export function useGlyphReplay() {
  const [replays, setReplays] = useState<ReplayItem[]>([]);
  const [latestTrace, setLatestTrace] = useState<LatestTrace | null>(null);

  useEffect(() => {
    fetch("/api/replay")
      .then((res) => res.json())
      .then((data) => setReplays(data));
  }, []);

  const handleReplayClick = (replay: ReplayItem) => {
    setLatestTrace({
      glyph: replay.glyph,
      action: replay.content,
      timestamp: replay.timestamp,
    });
  };

  return { replays, latestTrace, handleReplayClick };
}
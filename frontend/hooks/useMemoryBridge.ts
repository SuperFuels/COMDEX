import { useMemo, useState } from "react";
import useWebSocket from "@/hooks/useWebSocket";

interface MemoryGlyph {
  symbol: string;
  glyph_id: string;
  memory_weight?: number;
  entangled?: string[]; // glyph_ids
  collapse_state?: string;
}

export type MemoryBridge = {
  from: string; // symbol of origin glyph
  to: string;   // symbol of entangled glyph
  weight?: number;
};

export function useMemoryBridge(
  containerId: string
): { activeBridges: MemoryBridge[]; memoryGlyphs: MemoryGlyph[] } {
  const [memoryGlyphs, setMemoryGlyphs] = useState<MemoryGlyph[]>([]);

  const wsUrl = `/ws/glyphnet/${containerId}`;

  // Your hook expects (url, onMessage). It returns { socket, connected, emit } and
  // does NOT expose `lastJsonMessage`, so handle messages here.
  useWebSocket(wsUrl, (msg: any) => {
    const event = msg?.event ?? msg?.type;
    if (event === "memory_sync") {
      const glyphs = msg?.payload?.glyphs ?? msg?.glyphs;
      if (Array.isArray(glyphs)) {
        setMemoryGlyphs(glyphs as MemoryGlyph[]);
      }
    }
  });

  const glyphMap = useMemo(() => {
    const map: Record<string, MemoryGlyph> = {};
    for (const g of memoryGlyphs) map[g.glyph_id] = g;
    return map;
  }, [memoryGlyphs]);

  const activeBridges = useMemo<MemoryBridge[]>(() => {
    const bridges: MemoryBridge[] = [];
    for (const glyph of memoryGlyphs) {
      const fromSymbol = glyph.symbol;
      const entangledIds = glyph.entangled ?? [];
      for (const toId of entangledIds) {
        const toGlyph = glyphMap[toId];
        if (toGlyph?.symbol) {
          bridges.push({
            from: fromSymbol,
            to: toGlyph.symbol,
            weight: glyph.memory_weight ?? 1.0,
          });
        }
      }
    }
    return bridges;
  }, [memoryGlyphs, glyphMap]);

  return { activeBridges, memoryGlyphs };
}
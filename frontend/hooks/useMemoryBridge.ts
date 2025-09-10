import { useEffect, useMemo, useState } from "react";
import { useWebSocket } from "@/hooks/useWebSocket";

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

export function useMemoryBridge(containerId: string): {
  activeBridges: MemoryBridge[];
  memoryGlyphs: MemoryGlyph[];
} {
  const [memoryGlyphs, setMemoryGlyphs] = useState<MemoryGlyph[]>([]);
  const wsUrl = `/ws/glyphnet/${containerId}`;
  const { lastJsonMessage } = useWebSocket(wsUrl);

  useEffect(() => {
    if (lastJsonMessage?.event === "memory_sync") {
      const { glyphs } = lastJsonMessage.payload || {};
      if (Array.isArray(glyphs)) {
        setMemoryGlyphs(glyphs);
      }
    }
  }, [lastJsonMessage]);

  const glyphMap = useMemo(() => {
    const map: { [glyph_id: string]: MemoryGlyph } = {};
    for (const g of memoryGlyphs) {
      map[g.glyph_id] = g;
    }
    return map;
  }, [memoryGlyphs]);

  const activeBridges = useMemo(() => {
    const bridges: MemoryBridge[] = [];

    for (const glyph of memoryGlyphs) {
      const fromSymbol = glyph.symbol;
      const entangledIds = glyph.entangled || [];

      for (const toId of entangledIds) {
        const toGlyph = glyphMap[toId];
        if (toGlyph && toGlyph.symbol) {
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
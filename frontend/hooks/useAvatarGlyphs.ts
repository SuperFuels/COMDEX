import { useState } from "react";
import useWebSocket from "./useWebSocket";

// Minimal glyph shape we actually use here.
// (Avoids depending on a missing "@/types/glyph")
export type GlyphTraceEntry = {
  symbol: string;
  glyph_id?: string;
  trigger_state?: string;
  [k: string]: unknown;
};

/**
 * Live list of "interesting" avatar glyphs for a container.
 * Filters to symbols we care about or anything currently "triggered".
 */
export function useAvatarGlyphs(containerId: string): GlyphTraceEntry[] {
  const [activeGlyphs, setActiveGlyphs] = useState<GlyphTraceEntry[]>([]);

  // Our useWebSocket expects (url, onMessage, options?)
  useWebSocket(`/ws/glyphnet/${containerId}`, (raw: unknown) => {
    const msg = typeof raw === "string" ? safeParse(raw) : (raw as any);

    if (msg?.event === "glyph_trace") {
      const glyphs = (msg.payload?.glyphs ?? []) as GlyphTraceEntry[];
      if (Array.isArray(glyphs)) {
        const filtered = glyphs.filter(
          (g) =>
            ["↔", "⧖", "⬁", "🧠"].includes(g.symbol) ||
            g.trigger_state === "triggered"
        );
        setActiveGlyphs(filtered);
      }
    }
  });

  return activeGlyphs;
}

function safeParse(s: string) {
  try {
    return JSON.parse(s);
  } catch {
    return null;
  }
}
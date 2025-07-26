import { useEffect, useState } from "react";
import { GlyphTraceEntry } from "@/types/glyph";
import { useWebSocket } from "@/hooks/useWebSocket";

// Optionally parameterize this by containerId or HUD scope
export function useAvatarGlyphs(containerId: string) {
  const [activeGlyphs, setActiveGlyphs] = useState<GlyphTraceEntry[]>([]);
  const wsUrl = `/ws/glyphnet/${containerId}`;
  const { lastJsonMessage } = useWebSocket(wsUrl);

  useEffect(() => {
    if (lastJsonMessage?.event === "glyph_trace") {
      const { glyphs } = lastJsonMessage.payload || {};
      if (glyphs?.length) {
        const filtered = glyphs.filter((g: GlyphTraceEntry) =>
          ["↔", "⧖", "⬁", "🧠"].includes(g.symbol) || g.trigger_state === "triggered"
        );
        setActiveGlyphs(filtered);
      }
    }
  }, [lastJsonMessage]);

  return activeGlyphs;
}
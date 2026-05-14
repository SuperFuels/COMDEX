import { GlyphNode } from "@/types/qfc";

export async function pull_to_field(
  glyph: GlyphNode,
  containerId: string,
  emit?: (event: string, data: any) => void
) {
  const newNode = {
    ...glyph,
    id: `pulled-${Date.now()}`, // Unique ID for new node
    position: [
      glyph.position[0] + 1.5,
      glyph.position[1] + 0.5,
      glyph.position[2],
    ],
    label: glyph.label || "Pulled Glyph",
    source: "pull_to_field",
    tick: Date.now(),
  };

  const qfcUpdate = {
    containerId,
    nodes: [newNode],
    links: [],
    meta: {
      type: "pull_to_field",
      origin: "scroll_suggestion",
    },
  };

  // 🔁 Send live update to QFC via WebSocket
  if (emit) {
    emit("qfc_update", qfcUpdate);
  } else {
    console.warn("⚠️ No WebSocket emitter provided to pull_to_field");
  }
}
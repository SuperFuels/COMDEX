import React from "react";
import type { Presence } from "./types";

type PresenceLayerProps = {
  others: Presence[];
  zoom?: number; // optional, for scaled canvases
  offset?: { x: number; y: number }; // optional, if canvas is translated
};

export function PresenceLayer({ others, zoom = 1, offset = { x: 0, y: 0 } }: PresenceLayerProps) {
  return (
    <div className="pointer-events-none fixed inset-0 z-50">
      {others.map((p) => {
        if (!p.cursor) return null;

        const [x, y] = p.cursor;
        const left = x * zoom + offset.x;
        const top = y * zoom + offset.y;

        return (
          <div
            key={p.id}
            style={{
              left,
              top,
              position: "absolute",
              transform: "translate(-50%, -100%)",
              transition: "transform 0.08s ease-out, left 0.1s ease-out, top 0.1s ease-out",
              zIndex: 1,
            }}
          >
            <div
              style={{
                background: p.color,
                color: "white",
                padding: "2px 6px",
                borderRadius: 6,
                fontSize: 12,
                whiteSpace: "nowrap",
                boxShadow: "0 1px 4px rgba(0,0,0,0.3)",
                transform: "translateY(-4px)",
              }}
            >
              ▲ {p.name}
            </div>
          </div>
        );
      })}
    </div>
  );
}
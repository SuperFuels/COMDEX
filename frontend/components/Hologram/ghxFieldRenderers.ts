// File: frontend/components/Hologram/ghxFieldRenderers.ts

import { SQIColorMap } from "@/lib/sqiColors";
import { GHXBeam, CollapseEvent, PatternOverlay } from "@/types/ghx_types";

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 🎯 Render GHX Beam Path
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export function renderGHXBeam(
  ctx: CanvasRenderingContext2D,
  beam: GHXBeam
) {
  if (beam.path.length < 2) return;

  ctx.beginPath();
  ctx.moveTo(beam.path[0].x, beam.path[0].y);

  for (let i = 1; i < beam.path.length; i++) {
    ctx.lineTo(beam.path[i].x, beam.path[i].y);
  }

  const color = SQIColorMap[beam.sqiLevel] || "#00ffff";
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.setLineDash(beam.isEntangled ? [4, 2] : []);
  ctx.stroke();
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 💥 Render Collapse Event (Symbolic Compression)
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export function renderGlyphCollapse(
  ctx: CanvasRenderingContext2D,
  collapse: CollapseEvent
) {
  const { x, y } = collapse.position;
  const radius = 6;

  ctx.beginPath();
  ctx.arc(x, y, radius, 0, 2 * Math.PI);
  ctx.fillStyle = "rgba(255, 0, 0, 0.5)";
  ctx.fill();

  ctx.lineWidth = 1.5;
  ctx.strokeStyle = "#ff0000";
  ctx.stroke();
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 🧬 Render Symbolic Pattern Overlay
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export function renderPatternOverlay(
  ctx: CanvasRenderingContext2D,
  overlay: PatternOverlay
) {
  ctx.save();
  ctx.strokeStyle = overlay.color || "#ffaa00";
  ctx.lineWidth = 1.2;
  ctx.setLineDash([2, 3]);

  overlay.paths.forEach((path) => {
    if (path.length < 2) return;
    ctx.beginPath();
    ctx.moveTo(path[0].x, path[0].y);
    for (let i = 1; i < path.length; i++) {
      ctx.lineTo(path[i].x, path[i].y);
    }
    ctx.stroke();
  });

  ctx.restore();
}
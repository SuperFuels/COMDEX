// File: frontend/lib/hologram/ghx_trail_utils.ts

import { SymbolicNode } from "@/lib/types/symbolic_types";

interface TrailOverlayMetadata {
  label: string;
  concept_match_score?: number;
  semantic_distance?: number;
  intensity?: number;
}

interface DrawTrailOptions {
  context: CanvasRenderingContext2D;
  nodes: SymbolicNode[];
  highlightNodeId?: string;
  strokeStyle?: string;
  lineWidth?: number;
  overlayMetadata?: TrailOverlayMetadata[]; // 🧠 Optional SymbolNet scores
}

/**
 * Draws a replay trail connecting symbolic nodes with optional heatmap overlay.
 */
export function drawReplayTrail({
  context,
  nodes,
  highlightNodeId,
  strokeStyle = "#00FFAA",
  lineWidth = 2,
  overlayMetadata = [],
}: DrawTrailOptions) {
  if (!context || nodes.length < 2) return;

  context.save();
  context.lineWidth = lineWidth;

  for (let i = 0; i < nodes.length - 1; i++) {
    const from = nodes[i].position;
    const to = nodes[i + 1].position;
    if (!from || !to) continue;

    // 🔥 Apply SymbolNet intensity as trail color
    const meta = overlayMetadata[i] || {};
    const match = meta.concept_match_score ?? 0;
    const intensity = meta.intensity ?? match;

    const alpha = Math.min(1, Math.max(0.1, intensity)); // Clamp alpha
    const heatColor = `rgba(${Math.floor(255 * (1 - match))}, ${Math.floor(255 * match)}, 100, ${alpha})`;

    context.beginPath();
    context.strokeStyle = heatColor;
    context.moveTo(from.x, from.y);
    context.lineTo(to.x, to.y);
    context.stroke();
  }

  context.restore();

  // ✨ Highlight active node with glow
  if (highlightNodeId) {
    const activeNode = nodes.find((n) => n.id === highlightNodeId);
    if (activeNode) drawNodeHighlight(context, activeNode);
  }
}

/**
 * Draws a glowing highlight around the specified node.
 */
function drawNodeHighlight(context: CanvasRenderingContext2D, node: SymbolicNode) {
  const { x, y } = node.position;
  context.save();
  context.beginPath();
  context.arc(x, y, 12, 0, 2 * Math.PI);
  context.strokeStyle = "rgba(255, 255, 0, 0.9)";
  context.shadowColor = "yellow";
  context.shadowBlur = 10;
  context.lineWidth = 4;
  context.stroke();
  context.restore();
}
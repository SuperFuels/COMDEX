// File: types/ghx_types.ts

// 🌌 A single 2D point on the canvas
export interface GHXPoint {
  x: number;
  y: number;
}

// 🌠 A symbolic beam drawn across the quantum field
export interface GHXBeam {
  path: GHXPoint[];
  sqiLevel: number;
  isEntangled?: boolean;
  beamId?: string;
  sourceId?: string;
  timestamp?: number;
}

// 💥 Represents a collapse/compression event at a point
export interface CollapseEvent {
  position: GHXPoint;
  collapseId?: string;
  strength?: number;
  timestamp?: number;
}

// 🧬 Symbolic pattern overlay drawn across the field
export interface PatternOverlay {
  paths: GHXPoint[][];
  color?: string;
  patternId?: string;
  label?: string;
}
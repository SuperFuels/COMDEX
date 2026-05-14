// backend/types/qfc.ts

export interface Glyph {
  id: string;
  coord: string;
  tag: string;
  value: string;
  action: string;
  label?: string; // ← add this
  prediction?: string; // ← add this
  predictionConfidence?: number; // ← add this
}

export interface GlyphNode {
  id: string;
  label: string;
  position: [number, number, number];
  emotion?: string;
  tick?: number;
  source?: string;
  entanglement?: any;
  entangled?: boolean;
  tranquilityScore?: number;
  containerId?: string;
  summary?: string;
  memorySummary?: string;
  intent?: string;
}

export interface Beam {
  id: string;
  sourceId: string;
  targetId: string;
  type: "logic" | "emotion" | "memory" | "entanglement" | "collapse" | string;
  strength?: number;
  tick?: number;
  label?: string;
  metadata?: Record<string, any>;
}
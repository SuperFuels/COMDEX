// frontend/types/index.ts
// ────────────────────────────────────────────────────────────────────────────
// Shared types across COMDEX + AION UI
// ────────────────────────────────────────────────────────────────────────────

export interface Deal {
  id: number;
  product_id: number;
  product_title: string;
  quantity_kg: number;
  total_price: number;
  status: 'negotiation' | 'confirmed' | 'completed' | 'cancelled';
  supplier_wallet_address: string | null;
  created_at: string;
  // (Add any other fields your API returns here)
}

export interface TraitMap {
  [trait: string]: number; // e.g. { "curiosity": 0.8 }
}

export interface Awareness {
  summary: string;
  context?: string;
}

// ────────────────────────────────────────────────────────────────────────────
// AION: Glyph type used in Container + Glyph Inspector views
// ────────────────────────────────────────────────────────────────────────────

export interface Glyph {
  coord: string;
  tag: string;
  value: string;
  action: string;
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
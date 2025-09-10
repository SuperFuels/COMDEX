// frontend/types/qfc.ts
// ──────────────────────────────────────────────────────────────
// Shared types for QFC: Glyphs, Beams, and Node Data Structures
// ──────────────────────────────────────────────────────────────

export interface Glyph {
  coord: string;     // symbolic coordinate (e.g. "⧖.2.1")
  tag: string;       // symbolic tag or meaning
  value: string;     // value at this glyph (could be raw or resolved)
  action: string;    // behavior/action type (e.g. "collapse", "link")
  locked?: boolean;
  source?: string;
}

export interface GlyphNode {
  id: string;                           // unique glyph ID (node UUID)
  label: string;                        // display label
  position: [number, number, number];   // 3D position on QFC
  emotion?: string;                     // optional emotion tag
  tick?: number;                        // logic tick or timestamp
  source?: string;                      // e.g. "pull_to_field", "memory"
  entanglement?: any;                   // linked nodes, glyphs, etc.
  entangled?: boolean;                  // true if node is entangled
  tranquilityScore?: number;            // optional logic score
  containerId?: string;                 // owning .dc container
  summary?: string;                     // memory or logic summary
  memorySummary?: string;               // alternate label
  intent?: string;                      // user/system intent
}

export interface Beam {
  id: string;                           // unique beam ID
  sourceId: string;                     // start node ID
  targetId: string;                     // end node ID
  type: "logic" | "emotion" | "memory" | "entanglement" | "collapse" | string; // type of beam
  strength?: number;                    // optional strength (0–1)
  tick?: number;                        // logic tick of creation
  label?: string;                       // optional display label
  metadata?: Record<string, any>;      // arbitrary beam data
}
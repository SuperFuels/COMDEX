// src/lib/types/dc.ts
export type DcGlyph = {
  id?: string;
  symbol?: string;   // e.g. "↔", "⟲", etc.
  text?: string;     // optional text payload
  meta?: any;
};

export type DcContainer = {
  id: string;
  type: string;      // "container" | "page" | etc.
  glyphs?: DcGlyph[];
  meta?: any;
};
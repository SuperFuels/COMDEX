export type Vec3 = [number, number, number];

export interface AtomViz {
  glyph?: string;          // "↔" | "⧖" | "🧬" | etc.
  active?: boolean;        // highlight / spin
  logicDepth?: number;     // scale cue
  runtimeTick?: number;    // animation pulse
  soulLocked?: boolean;    // tiny scale if true
  position?: Vec3;         // scene placement
}

export interface AtomModel {
  id: string;
  containerId: string;
  kind?: string;           // "tool/lean", "data/*", etc.
  caps?: string[];
  tags?: string[];
  nodes?: string[];
  requires?: string[];
  produces?: string[];
  viz?: AtomViz;
}
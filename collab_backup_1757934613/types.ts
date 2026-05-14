// collab/types.ts
export type Vec3 = [number, number, number];

export type NodeRec = {
  id: string;
  position: Vec3;
  label?: string;
  tick?: number;
  collapse_state?: string;
  entropy?: number;
  containerId?: string;
  [k: string]: any;
};

export type LinkRec = {
  id: string;
  source: string;
  target: string;
  type?: string;
  isDream?: boolean;
  [k: string]: any;
};

export type BeamRec = {
  id: string;
  source: Vec3;
  target: Vec3;
  predicted?: boolean;
  collapse_state?: string;
  sqiScore?: number;
  [k: string]: any;
};

export type Presence = {
  id: string;
  name: string;
  color: string;
  role: "viewer" | "editor" | "agent" | "admin";
  cursor?: [number, number];
  selectionGlyphIds?: string[];
  viewport?: { center: Vec3; zoom: number };
};
export interface SymbolicNode {
  id: string;
  label: string;
  type: string;
  depth: number;
  position: {
    x: number;
    y: number;
    z: number;
  };
  morphic_overlay: MorphicOverlay;
  glyph_id: string;
  entangled_ids: string[];
  agent_id?: string;
  qglyph?: QGlyph;
  children: SymbolicNode[];
}

export interface MorphicOverlay {
  goal_match: number;
  entropy: number;
  mutation_path?: string[];
  node_type: string;
  is_prediction: boolean;
}

export interface QGlyph {
  id: string;
  state: string;
  probability?: number;
  [key: string]: any; // extensible for quantum state data
}

// Used when fetching from backend
export interface HolographicTree {
  tree_id: string;
  root: SymbolicNode;
  nodes: SymbolicNode[]; // ✅ Added for link resolvers and GHX overlays
  timestamp: string;
  metadata?: Record<string, any>;
  fusion_enabled: boolean;
  supports_replay: boolean;
}

// Alias for use in components expecting root node directly
export type HolographicTreeRoot = SymbolicNode;

export interface ReplayPath {
  path_id: string;
  glyph_sequence: string[];
  container_ids?: string[];
  mutation_trail?: string[];
  goal_trace?: string[];
  timestamp?: string;
}

export interface FusionPoint {
  node_id: string;
  source_agent?: string;
  target_agent?: string;
  fusion_score: number;
  linked_node_ids: string[];
}
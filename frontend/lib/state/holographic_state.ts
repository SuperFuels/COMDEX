import { create } from 'zustand';

interface SymbolicNode {
  id: string;
  label: string;
  type: string;
  depth: number;
  position: { x: number; y: number; z: number };
  morphic_overlay: any;
  glyph_id: string;
  entangled_ids: string[];
  agent_id?: string;
  qglyph?: any;
  children: SymbolicNode[];
}

interface SymbolicTree {
  tree_id: string;
  root: SymbolicNode;
  timestamp: string;
  metadata: Record<string, any>;
  fusion_enabled: boolean;
  supports_replay: boolean;
}

interface HolographicState {
  activeContainerId: string | null;
  setActiveContainerId: (id: string | null) => void;

  treeData: SymbolicTree | null;
  setTreeData: (tree: SymbolicTree | null) => void;

  currentNodeId: string | null;
  setCurrentNodeId: (id: string | null) => void;
}

export const useHolographicState = create<HolographicState>((set) => ({
  activeContainerId: null,
  setActiveContainerId: (id) => set({ activeContainerId: id }),

  treeData: null,
  setTreeData: (tree) => set({ treeData: tree }),

  currentNodeId: null,
  setCurrentNodeId: (id) => set({ currentNodeId: id }),
}));
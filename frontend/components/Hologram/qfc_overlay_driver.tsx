// File: QFCOverlayDriver.tsx

import React, { useEffect, useState } from 'react';
import GHXVisualizer from './GHXVisualizer';
import GHXReplaySlider from './GHXReplaySlider';
import GHXSignatureTrail from './GHXSignatureTrail';
import axios from 'axios';

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

interface TrailOverlayMetadata {
  label: string;
  concept_match_score?: number;
  semantic_distance?: number;
  intensity?: number;
}

interface SymbolicTree {
  tree_id: string;
  root: SymbolicNode;
  timestamp: string;
  metadata: Record<string, any>;
  fusion_enabled: boolean;
  supports_replay: boolean;
  symbolnetOverlay?: TrailOverlayMetadata[];
}

interface QFCOverlayDriverProps {
  containerId: string;
}

export const QFCOverlayDriver: React.FC<QFCOverlayDriverProps> = ({ containerId }) => {
  const [tree, setTree] = useState<SymbolicTree | null>(null);
  const [currentNodeId, setCurrentNodeId] = useState<string | null>(null);

  useEffect(() => {
    const fetchTree = async () => {
      try {
        const response = await axios.get(`/api/qfc/holographic_tree/${containerId}`);
        const fetchedTree = response.data.tree;

        if (!fetchedTree) {
          console.warn(`[QFCOverlayDriver] No tree returned for container: ${containerId}`);
        }

        setTree(fetchedTree);
      } catch (err) {
        console.error('[QFCOverlayDriver] ❌ Error loading QFC holographic tree:', err);
      }
    };

    fetchTree();
  }, [containerId]);

  const handleSliderChange = (nodeId: string) => {
    setCurrentNodeId(nodeId);
  };

  if (!tree) return <div className="text-sm text-gray-400">Loading symbolic overlay...</div>;

  return (
    <div className="qfc-overlay-container relative w-full h-full">
      <GHXReplaySlider tree={tree} onNodeChange={handleSliderChange} />

      <GHXVisualizer
        rootNode={tree.root}
        currentNodeId={currentNodeId}
        highlightMode="goal-vs-mutation"
        entanglementLines
        showQGlyphs
      />

      <GHXSignatureTrail
        tree={tree}
        currentNodeId={currentNodeId}
        overlayMetadata={tree.symbolnetOverlay || []}
      />
    </div>
  );
};
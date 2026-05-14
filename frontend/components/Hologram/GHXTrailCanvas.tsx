// File: frontend/components/hologram/GHXTrailCanvas.tsx

import React, { useEffect, useRef } from 'react';
import { drawReplayTrail } from '@/lib/hologram/ghx_trail_utils';
import { useHolographicState } from '@/lib/state/holographic_state';

const GHXTrailCanvas: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const { treeData, currentNodeId } = useHolographicState();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !treeData) return;

    const context = canvas.getContext('2d');
    if (!context) return;

    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Clear and draw
    context.clearRect(0, 0, canvas.width, canvas.height);
    const nodes: any[] = flattenTreeToList(treeData.root); // You may refine this.

    drawReplayTrail({
      context,
      nodes,
      highlightNodeId: currentNodeId || undefined,
      strokeStyle: '#00FFAA',
      lineWidth: 2,
    });

    return () => {
      window.removeEventListener('resize', resizeCanvas);
    };
  }, [treeData, currentNodeId]);

  return (
    <canvas
      ref={canvasRef}
      className="absolute top-0 left-0 w-full h-full pointer-events-none z-10"
    />
  );
};

export default GHXTrailCanvas;

/**
 * Flattens the symbolic tree into a list for trail rendering.
 */
function flattenTreeToList(root: any): any[] {
  const list: any[] = [];
  const stack = [root];
  while (stack.length) {
    const node = stack.pop();
    if (!node) continue;
    list.push(node);
    if (node.children) stack.push(...node.children);
  }
  return list.sort((a, b) => a.depth - b.depth);
}
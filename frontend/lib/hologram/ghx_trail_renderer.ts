import { SymbolicNode } from '../types/symbolic_types';

interface RenderTrailOptions {
  context: CanvasRenderingContext2D;
  rootNode: SymbolicNode;
  currentNodeId?: string | null;
  highlightMode?: 'goal-vs-mutation' | 'qglyphs-only' | 'entanglement';
}

/**
 * Recursively renders symbolic replay trail and connections between nodes.
 */
export function renderSymbolicTrail({
  context,
  rootNode,
  currentNodeId,
  highlightMode = 'goal-vs-mutation',
}: RenderTrailOptions): void {
  const renderNode = (node: SymbolicNode, parent?: SymbolicNode) => {
    const { x, y } = node.position;

    // Highlight current node if matched
    if (node.id === currentNodeId) {
      context.beginPath();
      context.arc(x, y, 6, 0, 2 * Math.PI);
      context.fillStyle = '#ffffff';
      context.fill();
    }

    // Draw node based on type or highlight mode
    context.beginPath();
    context.arc(x, y, 4, 0, 2 * Math.PI);
    context.fillStyle = getNodeColor(node, highlightMode);
    context.fill();

    // Draw edge to parent
    if (parent) {
      context.beginPath();
      context.moveTo(parent.position.x, parent.position.y);
      context.lineTo(x, y);
      context.strokeStyle = '#888888';
      context.lineWidth = 1;
      context.stroke();
    }

    node.children.forEach((child) => renderNode(child, node));
  };

  renderNode(rootNode);
}

function getNodeColor(node: SymbolicNode, mode: string): string {
  if (mode === 'qglyphs-only' && !node.qglyph) return 'rgba(128,128,128,0.4)';
  if (mode === 'goal-vs-mutation') {
    if (node.type === 'goal') return '#00FFAA';
    if (node.type === 'mutation') return '#FFAA00';
  }
  if (mode === 'entanglement' && node.entangled_ids.length > 0) return '#AA66FF';
  return '#CCCCCC';
}

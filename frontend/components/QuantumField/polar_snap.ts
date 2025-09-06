// File: frontend/components/QuantumField/polar_snap.ts

import { GlyphNode } from "@/components/Hologram/quantum_field_canvas";

/**
 * Snap entangled nodes to a polar grid layout around a central glyph.
 * Used to create visually meaningful symmetry around entanglement centers.
 */
export function snapToPolarGrid(
  nodes: GlyphNode[],
  centerId: string,
  radius: number = 3,
  startAngle: number = 0
): GlyphNode[] {
  const centerNode = nodes.find((n) => n.id === centerId);
  if (!centerNode) return nodes;

  // Filter nodes that are entangled with the center node
  const entangledNodes = nodes.filter(
    (n) => n.id !== centerId && n.trailId === centerNode.trailId
  );

  const angleStep = (2 * Math.PI) / entangledNodes.length;

  // Arrange entangled nodes around the center in a polar circle
  const snappedNodes = nodes.map((node) => {
    if (!entangledNodes.includes(node)) return node;

    const index = entangledNodes.indexOf(node);
    const angle = startAngle + index * angleStep;

    const x = centerNode.position[0] + radius * Math.cos(angle);
    const y = centerNode.position[1];
    const z = centerNode.position[2] + radius * Math.sin(angle);

    return {
      ...node,
      position: [x, y, z] as [number, number, number],
    };
  });

  return snappedNodes;
}
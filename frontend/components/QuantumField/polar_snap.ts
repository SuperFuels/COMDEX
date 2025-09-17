// File: frontend/components/QuantumField/polar_snap.ts
import type { GlyphNode } from "@/types/qfc";

/**
 * Snap entangled nodes to a polar grid layout around a central glyph.
 * Tries several possible fields to determine "trail/group" membership:
 *   - trailId
 *   - trail_id
 *   - trail.id
 *   - entanglementTrailId / groupId (best-effort)
 * Falls back to checking an `entangled_with` array if no trail id is present.
 */
export function snapToPolarGrid(
  nodes: GlyphNode[],
  centerId: string,
  radius: number = 3,
  startAngle: number = 0
): GlyphNode[] {
  const centerNode = nodes.find((n) => n.id === centerId);
  if (!centerNode) return nodes;

  // Best-effort "trail/group" id getter without changing the GlyphNode type
  const getTrailId = (n: GlyphNode): string | undefined => {
    const anyN = n as any;
    return (
      anyN.trailId ??
      anyN.trail_id ??
      anyN.trail?.id ??
      anyN.entanglementTrailId ??
      anyN.groupId
    );
  };

  const centerTrail = getTrailId(centerNode);

  // Determine which nodes should orbit the center
  const entangledNodes = nodes.filter((n) => {
    if (n.id === centerId) return false;

    if (centerTrail != null) {
      return getTrailId(n) === centerTrail;
    }

    // Fallback: if a node lists entanglements, use that
    const ent = (n as any).entangled_with as string[] | undefined;
    return Array.isArray(ent) && ent.includes(centerId);
  });

  if (entangledNodes.length === 0) return nodes;

  const angleStep = (2 * Math.PI) / entangledNodes.length;

  // Arrange entangled nodes around the center in a polar circle
  return nodes.map((node) => {
    const index = entangledNodes.indexOf(node);
    if (index === -1) return node;

    const [cx, cy, cz] =
      ((centerNode as any).position as [number, number, number]) ?? [0, 0, 0];

    const angle = startAngle + index * angleStep;
    const x = cx + radius * Math.cos(angle);
    const y = cy;
    const z = cz + radius * Math.sin(angle);

    return {
      ...(node as any),
      position: [x, y, z] as [number, number, number],
    } as GlyphNode;
  });
}
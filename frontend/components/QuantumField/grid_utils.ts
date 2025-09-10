// File: frontend/components/QuantumField/grid_utils.ts

export type Position = [number, number, number];

/** 📐 Snap to Cartesian grid */
export function snapToGrid(
  position: Position,
  gridSize = 1
): Position {
  return position.map((v) => Math.round(v / gridSize) * gridSize) as Position;
}

/** 🧲 Snap nodes to polar grid around a central node */
export function snapToPolarGrid(
  nodes: { id: string; position: Position }[],
  centerId: string,
  radiusStep = 2,
  angleOffset = 0
) {
  const center = nodes.find((n) => n.id === centerId);
  if (!center) return nodes;

  const others = nodes.filter((n) => n.id !== centerId);
  const angleStep = (2 * Math.PI) / others.length;

  const snapped = others.map((node, i) => {
    const radius = radiusStep * (1 + Math.floor(i / 6));
    const angle = angleStep * i + angleOffset;
    const x = center.position[0] + radius * Math.cos(angle);
    const y = center.position[1] + radius * Math.sin(angle);
    const z = center.position[2] + (i % 2 === 0 ? 0 : 1); // ⬆️ subtle 3D

    return { ...node, position: snapToGrid([x, y, z], 0.5) };
  });

  return [center, ...snapped];
}

/** 🧱 Nest layers by tick */
export function snapToLayeredDepth(
  nodes: { id: string; tick?: number; position: Position }[],
  baseZ = 0,
  layerDepth = 1
) {
  return nodes.map((n) => {
    const tick = n.tick ?? 0;
    const z = baseZ + tick * layerDepth;
    return { ...n, position: [n.position[0], n.position[1], z] };
  });
}
// layout.ts

export function snapToEntangledMemoryLayout(
  nodes: any[],
  containerId: string
): any[] {
  const groupedByMemory: Record<string, any[]> = {};

  for (const node of nodes) {
    const key =
      node.memoryTrace?.containerId ||
      node.containerId ||
      "unknown";

    if (!groupedByMemory[key]) groupedByMemory[key] = [];
    groupedByMemory[key].push(node);
  }

  let angle = 0;
  const radius = 5;
  const groupCount = Object.keys(groupedByMemory).length;
  let groupIndex = 0;

  for (const [groupKey, groupNodes] of Object.entries(groupedByMemory)) {
    const groupAngle = (Math.PI * 2 * groupIndex) / groupCount;
    const centerX = Math.cos(groupAngle) * radius;
    const centerY = Math.sin(groupAngle) * radius;
    const centerZ = 0;

    groupNodes.forEach((node, i) => {
      const offset = (i / groupNodes.length) * Math.PI * 2;
      const x = centerX + Math.cos(offset) * 1.5;
      const y = centerY + Math.sin(offset) * 1.5;
      const z = centerZ;

      node.position = [x, y, z];
    });

    groupIndex++;
  }

  return nodes;
}
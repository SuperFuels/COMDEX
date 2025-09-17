// frontend/lib/hologram/entanglement_link_resolver.ts

import { HolographicTree, SymbolicNode } from "@/lib/types/symbolic_types";

export interface EntanglementResolutionResult {
  forwardMap: Record<string, Set<string>>;
  reverseMap: Record<string, Set<string>>;
  unresolvedLinks: { fromId: string; missingId: string }[];
  bidirectionalLinks: [string, string][];
  unidirectionalLinks: [string, string][];
}

export function resolveEntanglementLinks(
  tree: HolographicTree
): EntanglementResolutionResult {
  const forwardMap: Record<string, Set<string>> = {};
  const reverseMap: Record<string, Set<string>> = {};
  const unresolvedLinks: { fromId: string; missingId: string }[] = [];
  const bidirectionalLinks: [string, string][] = [];
  const unidirectionalLinks: [string, string][] = [];

  const nodeMap: Record<string, SymbolicNode> = {};
  for (const node of tree.nodes) {
    nodeMap[node.id] = node;
  }

  for (const node of tree.nodes) {
    const fromId = node.id;
    const entangled = node.entangled_ids || [];
    forwardMap[fromId] = new Set(entangled);

    for (const toId of entangled) {
      if (!nodeMap[toId]) {
        unresolvedLinks.push({ fromId, missingId: toId });
        continue;
      }

      if (!reverseMap[toId]) reverseMap[toId] = new Set();
      reverseMap[toId].add(fromId);
    }
  }

  // Build directional info
  for (const fromId in forwardMap) {
    for (const toId of forwardMap[fromId]) {
      const reverse = reverseMap[fromId]?.has(toId);
      if (reverse) {
        bidirectionalLinks.push([fromId, toId]);
      } else {
        unidirectionalLinks.push([fromId, toId]);
      }
    }
  }

  return {
    forwardMap,
    reverseMap,
    unresolvedLinks,
    bidirectionalLinks,
    unidirectionalLinks,
  };
}
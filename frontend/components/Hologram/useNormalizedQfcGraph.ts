// File: frontend/components/Hologram/useNormalizedQfcGraph.ts
import { useMemo } from "react";
import { GlyphNode } from "@/types/qfc";

type Link = {
  source: string;
  target: string;
  type?: "entangled" | "teleport" | "logic";
  tick?: number;
};

type ExtendedGlyphNode = GlyphNode & {
  id?: string | number;
  position: [number, number, number];
  containerId?: string;
  predicted?: boolean;
  locked?: boolean;
  color?: string;
  label?: string;
  emotion?: { type?: string; intensity?: number } | boolean;
};

function normalizeNodes(sharedNodes: any[] | undefined): ExtendedGlyphNode[] {
  return (sharedNodes ?? []).map((n: any) => ({
    ...n,
    id: n.id,
    position: (n.position ?? [0, 0, 0]) as [number, number, number],
    label: typeof n.label === "string" ? n.label : String(n.id ?? ""),
  }));
}

function normalizeLinks(sharedLinks: any[] | undefined): Link[] {
  return (sharedLinks ?? []).map((l: any) => ({
    ...l,
    source: String(l.source),
    target: String(l.target),
  }));
}

/** Minimal merge/filter to mirror your previous local util */
function mergePredictedGraphLocal(args: {
  nodes: GlyphNode[];
  links: Link[];
  tickFilter?: number;
  showCollapsed?: boolean;
  // predictedNodes?: GlyphNode[];
  // predictedLinks?: Link[];
}) {
  const { nodes, links, tickFilter, showCollapsed } = args;

  const filteredNodes = (nodes ?? []).filter((n: any) => {
    // respect tick filter if present
    if (typeof tickFilter === "number" && typeof n?.tick === "number") {
      if (n.tick !== tickFilter) return false;
    }
    // hide collapsed if requested
    if (!showCollapsed && n?.collapse_state === "collapsed") return false;
    return true;
  });

  const nodeIds = new Set(filteredNodes.map((n: any) => String(n.id)));
  const filteredLinks = (links ?? []).filter(
    (l) => nodeIds.has(String(l.source)) && nodeIds.has(String(l.target))
  );

  return {
    mergedNodes: filteredNodes as unknown as ExtendedGlyphNode[],
    mergedLinks: filteredLinks,
  };
}

export function useNormalizedQfcGraph(params: {
  propsNodes: ExtendedGlyphNode[] | undefined;
  propsLinks: Link[] | undefined;
  sharedNodes: any[] | undefined;
  sharedLinks: any[] | undefined;
  sharedBeams: any[] | undefined;
  tickFilter?: number;
  showCollapsed?: boolean;
}) {
  const {
    propsNodes,
    propsLinks,
    sharedNodes,
    sharedLinks,
    sharedBeams,
    tickFilter,
    showCollapsed,
  } = params;

  const normSharedNodes = useMemo(
    () => normalizeNodes(sharedNodes),
    [sharedNodes]
  );

  const normSharedLinks = useMemo(
    () => normalizeLinks(sharedLinks),
    [sharedLinks]
  );

  // Prefer CRDT data; fall back to props
  const nodes: ExtendedGlyphNode[] =
    normSharedNodes.length > 0 ? normSharedNodes : (propsNodes ?? []);

  const links: Link[] =
    normSharedLinks.length > 0 ? normSharedLinks : (propsLinks ?? []);

  const effectiveBeams = (sharedBeams ?? []).length > 0 ? sharedBeams! : [];

  const useFallback =
    normSharedNodes.length === 0 && normSharedLinks.length === 0;

  const { mergedNodes, mergedLinks } = useMemo(
    () =>
      mergePredictedGraphLocal({
        nodes: nodes as unknown as GlyphNode[],
        links,
        tickFilter,
        showCollapsed,
      }),
    [nodes, links, tickFilter, showCollapsed]
  );

  return {
    nodes,
    links,
    effectiveBeams,
    useFallback,
    mergedNodes,
    mergedLinks,
  };
}

export type { ExtendedGlyphNode, Link };
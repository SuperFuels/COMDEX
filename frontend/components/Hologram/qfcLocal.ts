// File: frontend/components/Hologram/qfcLocal.ts
import { useEffect } from "react";
import { GlyphNode } from "@/types/qfc";

/** Safe getter bound to a nodes array */
export const getNodeByIdLocal = (nodes: GlyphNode[], id: string) =>
  nodes.find((n: any) => (n as any).id === id);

/** Load mixed test beams (original /api/test-mixed-beams fetch) */
export function useLoadQWaveBeamsLocal(
  setBeamData: React.Dispatch<React.SetStateAction<any[] | null>>
) {
  useEffect(() => {
    let alive = true;
    fetch("/api/test-mixed-beams")
      .then((res) => res.json())
      .then((data) => alive && setBeamData(data))
      .catch(() => void 0);
    return () => {
      alive = false;
    };
  }, [setBeamData]);
}

/** Your static trails, returned so you can use them inline */
export function getStaticTrailsLocal() {
  const collapseTrails = [
    {
      id: "trail-1",
      path: [
        [0, 0, 0],
        [1, 2, 0],
        [2, 4, 0],
      ] as [number, number, number][],
      color: "#ffaa00",
    },
  ];

  const breakthroughTrails = [
    {
      points: [
        [0, 0, 0],
        [1.5, 0.5, 0],
        [2.2, 1.2, 0],
      ] as [number, number, number][],
      type: "breakthrough",
    },
  ];

  const deadendTrails = [
    {
      points: [
        [1, -1, 0],
        [1.5, -1.5, 0],
        [2.0, -2.0, 0],
      ] as [number, number, number][],
      type: "deadend",
    },
  ];

  return { collapseTrails, breakthroughTrails, deadendTrails };
}

/** Merge predicted nodes/links into the main graph (preserves your behavior) */
export function mergePredictedGraphLocal(params: {
  nodes: GlyphNode[];
  links: { source: string; target: string; tick?: number }[];
  tickFilter?: number;
  showCollapsed?: boolean;
  predictedNodes?: GlyphNode[];
  predictedLinks?: { source: string; target: string; tick?: number }[];
}) {
  const {
    nodes,
    links,
    tickFilter,
    showCollapsed = true,
    predictedNodes = [],
    predictedLinks = [],
  } = params;

  const mergedNodes: GlyphNode[] = [
    ...nodes.filter((node) => {
      const matchTick = tickFilter === undefined || (node as any).tick === tickFilter;
      const matchCollapse =
        showCollapsed || (node as any).collapse_state !== "collapsed";
      return matchTick && matchCollapse;
    }),
    ...predictedNodes
      .filter((pn) => !nodes.some((n) => (n as any).id === (pn as any).id))
      .map((pn) => ({ ...(pn as any), isDream: true as const })),
  ];

  const mergedLinks = [
    ...links.filter((link) => tickFilter === undefined || link.tick === tickFilter),
    ...predictedLinks
      .filter((pl) => !links.some((l) => l.source === pl.source && l.target === pl.target))
      .map((pl) => ({ ...pl, isDream: true as const })),
  ];

  return { mergedNodes, mergedLinks };
}
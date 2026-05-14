// File: frontend/components/Hologram/QuantumFieldCanvasLoader.tsx
'use client';

import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { snapToEntangledMemoryLayout } from "@/lib/layout";
import { useQfcSocket } from "@/hooks/useQfcSocket";
import { QFCFocusProvider } from "@/components/QuantumField/qfc_focus_context";

// Dynamically load the R3F canvas wrapper (no SSR)
const QuantumFieldCanvas = dynamic(
  () => import("./quantum_field_canvas"),
  { ssr: false }
);

type LoaderProps = {
  containerId: string;
  tickFilter?: number;
  showCollapsed?: boolean;
  onTeleport?: (id: string) => void;
};

type GraphState = {
  nodes: any[];
  links: any[];
  beams?: any[];
};

export const QuantumFieldCanvasLoader: React.FC<LoaderProps> = ({
  containerId,
  tickFilter,
  showCollapsed,
  onTeleport,
}) => {
  const [data, setData] = useState<GraphState>({
    nodes: [],
    links: [],
    beams: [],
  });

  // Try rich QFC view first (with layout + traces), then fall back to basic graph
  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const res = await fetch(`/api/qfc_view/${encodeURIComponent(containerId)}`);
        if (!res.ok) throw new Error(String(res.statusText));
        const json = await res.json();

        const rawNodes: any[] = Array.isArray(json?.nodes) ? json.nodes : [];
        const links: any[] = Array.isArray(json?.links) ? json.links : [];
        const beams: any[] = Array.isArray(json?.beams) ? json.beams : [];

        // Optional layout snap
        const snapped = snapToEntangledMemoryLayout(rawNodes, containerId);

        // Annotate
        const annotated = snapped.map((node: any) => {
          const glyphTrace = node.glyphTrace ?? node.memory ?? null;

          let goalType: "goal" | "strategy" | "milestone" | null = null;
          const label = String(node.label ?? "").toLowerCase();
          if (label.includes("goal")) goalType = "goal";
          else if (label.includes("strategy")) goalType = "strategy";
          else if (label.includes("milestone")) goalType = "milestone";

          let memoryTrace = null;
          if (Array.isArray(glyphTrace) && glyphTrace.length > 0) {
            const last = glyphTrace[glyphTrace.length - 1] ?? {};
            memoryTrace = {
              summary: last.summary ?? last.intent ?? "Observed symbolic memory",
              containerId: node.containerId ?? containerId,
              agentId: node.agentId ?? "aion-agent",
            };
          }

          return {
            ...node,
            goalType,
            memoryTrace,
            containerId: node.containerId ?? containerId ?? "default.dc.json",
          };
        });

        if (!cancelled) {
          setData({ nodes: annotated, links, beams });
        }
        return; // success path done
      } catch {
        // continue to fallback
      }

      // Fallback: /api/qfc/graph
      try {
        const r = await fetch(
          `/api/qfc/graph?container_id=${encodeURIComponent(containerId)}`
        );
        const j = r.ok ? await r.json() : { nodes: [], links: [], beams: [] };
        if (!cancelled) {
          setData({
            nodes: Array.isArray(j.nodes) ? j.nodes : [],
            links: Array.isArray(j.links) ? j.links : [],
            beams: Array.isArray(j.beams) ? j.beams : [],
          });
        }
      } catch {
        if (!cancelled) setData({ nodes: [], links: [], beams: [] });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [containerId]);

  // Live updates from socket – merge by id (nodes) and tuple (links)
  useQfcSocket(containerId, (payload: any) => {
    if (!payload) return;
    setData((prev) => {
      const incomingNodes: any[] = Array.isArray(payload.nodes) ? payload.nodes : [];
      const incomingLinks: any[] = Array.isArray(payload.links) ? payload.links : [];
      const incomingBeams: any[] = Array.isArray(payload.beams) ? payload.beams : [];

      // merge nodes by id
      const byId = new Map<string, any>();
      const mergedNodes: any[] = [];
      for (const n of prev.nodes) {
        const id = String(n.id);
        byId.set(id, n);
        mergedNodes.push(n);
      }
      for (const n of incomingNodes) {
        const id = String(n.id);
        if (byId.has(id)) {
          const merged = { ...byId.get(id), ...n };
          byId.set(id, merged);
          const idx = mergedNodes.findIndex((m) => String(m.id) === id);
          if (idx !== -1) mergedNodes[idx] = merged;
        } else {
          byId.set(id, n);
          mergedNodes.push(n);
        }
      }

      // merge links by (source,target,type)
      const keyOf = (l: any) => `${l.source}->${l.target}:${l.type ?? ""}`;
      const seen = new Set<string>();
      const mergedLinks: any[] = [];
      for (const l of [...prev.links, ...incomingLinks]) {
        const k = keyOf(l);
        if (seen.has(k)) continue;
        seen.add(k);
        mergedLinks.push(l);
      }

      // beams: simplest is “last write wins”
      const mergedBeams = incomingBeams.length ? incomingBeams : prev.beams ?? [];

      return { nodes: mergedNodes, links: mergedLinks, beams: mergedBeams };
    });
  });

  // Render the canvas, wrapped in QFCFocusProvider so useQFCFocus works
  return (
    <QFCFocusProvider>
      <QuantumFieldCanvas
        nodes={data.nodes as any}
        links={data.links as any}
        beams={data.beams as any}
        containerId={containerId}
        tickFilter={tickFilter}
        showCollapsed={showCollapsed}
        onTeleport={onTeleport}
      />
    </QFCFocusProvider>
  );
};

export default QuantumFieldCanvasLoader;
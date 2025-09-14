// File: frontend/components/Hologram/QuantumFieldCanvasLoader.tsx
import React, { useEffect, useState } from "react";
import { snapToEntangledMemoryLayout } from "@/lib/layout";
import { useQfcSocket } from "@/hooks/useQfcSocket";
import QuantumFieldCanvas from "./quantum_field_canvas";

type LoaderProps = {
  containerId: string;
  tickFilter?: number;
  showCollapsed?: boolean;
  onTeleport?: (id: string) => void;
};

type GraphState = { nodes: any[]; links: any[] };

export const QuantumFieldCanvasLoader: React.FC<LoaderProps> = ({
  containerId,
  tickFilter,
  showCollapsed,
  onTeleport,
}) => {
  const [data, setData] = useState<GraphState>({ nodes: [], links: [] });

  // Try rich QFC view first (with layout + traces), then fall back to basic graph
  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const res = await fetch(`/api/qfc_view/${encodeURIComponent(containerId)}`);
        if (!res.ok) throw new Error(String(res.statusText));
        const json = await res.json();

        const rawNodes: any[] = json?.nodes ?? [];
        const links: any[] = json?.links ?? [];

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

        if (!cancelled) setData({ nodes: annotated, links });
        return; // success path done
      } catch {
        // continue to fallback
      }

      // Fallback: /api/qfc/graph
      try {
        const r = await fetch(
          `/api/qfc/graph?container_id=${encodeURIComponent(containerId)}`
        );
        const j = r.ok ? await r.json() : { nodes: [], links: [] };
        if (!cancelled) setData({ nodes: j.nodes ?? [], links: j.links ?? [] });
      } catch {
        if (!cancelled) setData({ nodes: [], links: [] });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [containerId]);

  // Live updates from socket – merge by id (nodes) and tuple (links)
  useQfcSocket(containerId, (payload: any) => {
    if (!payload) return;
    setData(prev => {
      const nextNodes: any[] = payload.nodes ?? [];
      const nextLinks: any[] = payload.links ?? [];

      // merge nodes by id
      const byId = new Map<string, any>();
      const mergedNodes: any[] = [];
      for (const n of prev.nodes) {
        byId.set(String(n.id), n);
        mergedNodes.push(n);
      }
      for (const n of nextNodes) {
        const id = String(n.id);
        if (byId.has(id)) {
          const merged = { ...byId.get(id), ...n };
          byId.set(id, merged);
          const idx = mergedNodes.findIndex(m => String(m.id) === id);
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
      for (const l of [...prev.links, ...nextLinks]) {
        const k = keyOf(l);
        if (seen.has(k)) continue;
        seen.add(k);
        mergedLinks.push(l);
      }

      return { nodes: mergedNodes, links: mergedLinks };
    });
  });

  // Render the canvas
  return (
    <QuantumFieldCanvas
      nodes={data.nodes as any}
      links={data.links as any}
      containerId={containerId}
      tickFilter={tickFilter}
      showCollapsed={showCollapsed}
      onTeleport={onTeleport}
    />
  );
};

export default QuantumFieldCanvasLoader;
// Glyph_Net_Browser/src/lib/rehydrate.ts
import type { HoloIR } from "./types/holo";
import type { GhxPacket } from "../components/DevFieldHologram3D";

export function buildPhotonStubFromHolo(holo: HoloIR | null): string | null {
  if (!holo) return null;

  const container = holo.container_id ?? "unknown_container";
  const motifId =
    (holo as any).metadata?.motif?.motif_id ??
    (holo as any).metadata?.motif?.id ??
    "unknown_motif";

  const header = [
    `# holo:${holo.holo_id}`,
    `# container:${container}`,
  ].join("\n");

  const nodeIds = (holo.ghx?.nodes ?? []).map((n: any) => n.id);
  const edgePairs = (holo.ghx?.edges ?? []).map((e: any) => ({
    src: e.source ?? e.src,
    dst: e.target ?? e.dst,
  }));

  const nodeLines = nodeIds.map((id) => `  node "${id}"  //`).join("\n");
  const edgeLines = edgePairs
    .filter((e) => e.src && e.dst)
    .map((e) => `  link "${e.src}" -> "${e.dst}"  //`)
    .join("\n");

  return [
    header,
    "",
    `motif "${motifId}" {`,
    "  // nodes",
    nodeLines || "  // (no nodes)",
    "",
    "  // edges",
    edgeLines || "  // (no edges)",
    "",
    "  // TODO: refine this motif in Photon",
    "}",
  ].join("\n");
}

// 🔁 moved here from DevFieldHologram3DContainer.tsx
export function buildGhxFromHolo(holo: HoloIR): GhxPacket {
  return {
    ghx_version: "1.0",
    origin: `holo:${holo.holo_id}`,
    container_id: holo.container_id,

    nodes: (holo.ghx?.nodes ?? []).map((n: any) => ({
      id: n.id,
      label: n.label,
      type: n.type ?? "holo_node",
      tags: n.tags ?? [],
      pos: n.pos,
      icon: n.icon,
      meta: n.meta ?? {},
      data: {
        ...(n.meta ?? {}),
        from: "holo",
      },
    })),

    edges: (holo.ghx?.edges ?? []).map((e: any, idx: number) => {
      const srcId = e.source ?? e.src;
      const dstId = e.target ?? e.dst;

      return {
        id: e.id ?? `holo-edge-${idx}`,
        src: srcId,
        dst: dstId,
        source: srcId,
        target: dstId,
        relation: e.relation,
        weight: e.weight,
        tags: e.tags ?? [],
        meta: e.meta ?? {},
        data: {
          relation: e.relation,
          ...(e.meta ?? {}),
          from: "holo",
        },
      };
    }),

    metadata: {
      holo_id: holo.holo_id,
      kind: (holo as any).kind,
      timefold: (holo as any).timefold,
      indexing: (holo as any).indexing,
    },
  };
}
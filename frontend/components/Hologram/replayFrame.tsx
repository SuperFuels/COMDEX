import * as React from "react";
import { Node } from "@/components/QuantumField/Node";
import { LinkLine } from "@/components/QuantumField/LinkLine";

export type ReplayNode = { id?: string | number; position: [number,number,number] };
export type ReplayLink = { source: string; target: string; type?: string; isDream?: boolean };

export function makeRenderReplayFrame(
  nodes: ReplayNode[],
  onTeleport?: (id: string) => void
) {
  const byId = new Map<string, ReplayNode>();
  nodes.forEach(n => {
    const id = String((n as any).id ?? "");
    if (id) byId.set(id, n);
  });

  return (frame: any) => (
    <>
      {(frame?.glyphs ?? []).map((node: any, i: number) => (
        <Node key={`replay-node-${node?.id ?? i}`} node={node} onTeleport={onTeleport} />
      ))}
      {(frame?.links ?? []).map((l: ReplayLink, i: number) => {
        const s = byId.get(String(l?.source));
        const t = byId.get(String(l?.target));
        if (!s || !t) return null;
        return (
          <LinkLine
            key={`replay-link-${i}`}
            source={s as any}
            target={t as any}
            type={l?.type}
            isDream={Boolean(l?.isDream)}
          />
        );
      })}
    </>
  );
}
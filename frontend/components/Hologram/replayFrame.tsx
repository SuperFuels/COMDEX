import * as React from "react";
import { Node } from "@/components/QuantumField/Node";
import { LinkLine } from "@/components/QuantumField/LinkLine";

export type ReplayNode = {
  id?: string | number;
  position: [number, number, number];
};

export type ReplayLink = {
  source: string;
  target: string;
  /** optional metadata you may use internally, but not passed to LinkLine */
  type?: string;
  isDream?: boolean;
};

export function makeRenderReplayFrame(
  nodes: ReplayNode[],
  onTeleport?: (id: string) => void
): (frame: any) => JSX.Element {
  const byId = new Map<string, ReplayNode>();
  for (const n of nodes) {
    const id = String((n as any).id ?? "");
    if (id) byId.set(id, n);
  }

  return (frame: any) => (
    <>
      {(frame?.glyphs ?? []).map((node: any, i: number) => (
        <Node
          key={`replay-node-${node?.id ?? i}`}
          node={node}
          onTeleport={onTeleport}
        />
      ))}

      {(frame?.links ?? []).map((l: ReplayLink, i: number) => {
        const s = byId.get(String(l?.source));
        const t = byId.get(String(l?.target));
        if (!s || !t) return null;

        // Only pass props that LinkLine actually supports.
        // (Remove 'type' and 'isDream' — they aren't in LinkLineProps.)
        return (
          <LinkLine
            key={`replay-link-${i}`}
            source={s as any}
            target={t as any}
          />
        );
      })}
    </>
  );
}
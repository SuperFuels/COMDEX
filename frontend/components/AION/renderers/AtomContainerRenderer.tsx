"use client";

import React from "react";
import AtomContainer from "@/components/ContainerMap/AtomContainer";
import type { AtomModel } from "@/types/atom";

export interface AtomContainerRendererProps {
  position: [number, number, number];
  container: {
    id: string;
    name: string;
    atoms?: AtomModel[];
    glyph?: string;
    runtime_tick?: number;
    logic_depth?: number;
    soul_locked?: boolean;
  };
}

/**
 * Matches the interface of the other renderers: { position, container }.
 * Fans out the container.atoms to your existing <AtomContainer atom={...} /> component.
 */
const AtomContainerRenderer: React.FC<AtomContainerRendererProps> = ({
  position,
  container,
}) => {
  const atoms = container.atoms ?? [];

  return (
    <group position={position}>
      {atoms.map((atom, i) => (
        <AtomContainer
          key={`${container.id}-${atom.id ?? i}`}
          atom={{
            ...atom,
            containerId: atom.containerId ?? container.id,
            viz: {
              ...(atom as any).viz,
              // stagger atoms around the container position
              position: [
                position[0] +
                  Math.cos(
                    (i / Math.max(atoms.length, 1)) * Math.PI * 2
                  ) *
                    2.2,
                position[1] + 0.4 * (i % 2 ? 1 : -1),
                position[2] +
                  Math.sin(
                    (i / Math.max(atoms.length, 1)) * Math.PI * 2
                  ) *
                    2.2,
              ] as [number, number, number],
            },
          }}
        />
      ))}
    </group>
  );
};

export default AtomContainerRenderer;
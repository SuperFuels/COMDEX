import React, { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import type { AtomModel, AtomViz, Vec3 } from "@/types/atom";

const AtomContainer = dynamic(() => import("../ContainerMap/AtomContainer"), {
  ssr: false,
  loading: () => null,
});

interface Props {
  atom: AtomModel;
  containerMetadata?: Record<string, any>;
  position?: Vec3;
}

export default function AtomContainerController({ atom, containerMetadata, position }: Props) {
  const [viz, setViz] = useState<AtomViz>(atom.viz ?? {});

  useEffect(() => {
    // derive a few defaults from container metadata if present
    const nextViz: AtomViz = {
      ...viz,
      active: containerMetadata?.active ?? viz.active ?? false,
      glyph: containerMetadata?.glyph ?? viz.glyph,
      logicDepth:
        typeof containerMetadata?.logicDepth === "number"
          ? containerMetadata.logicDepth
          : viz.logicDepth ?? 0,
      runtimeTick: containerMetadata?.runtimeTick ?? viz.runtimeTick ?? 0,
      soulLocked: containerMetadata?.soulLocked ?? viz.soulLocked ?? false,
      position: viz.position, // keep atom's own position by default
    };
    setViz(nextViz);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [containerMetadata]);

  const boundAtom = useMemo<AtomModel>(
    () => ({ ...atom, viz: { ...atom.viz, ...viz } }),
    [atom, viz]
  );

  return <AtomContainer atom={boundAtom} position={position} />;
}
// components/ContainerMap/HobermanSphereController.tsx
import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";

// Load whatever the module exports (default or named), and relax typing.
// This avoids duplicating the sphere's full prop type here.
const HobermanSphere = dynamic<any>(
  () =>
    import("./HobermanSphere").then((m: any) => m.default ?? m.HobermanSphere ?? m),
  { ssr: false, loading: () => null }
);

export interface HobermanSphereControllerProps {
  containerMetadata: Record<string, any>;
  position: [number, number, number];
}

const HobermanSphereController: React.FC<HobermanSphereControllerProps> = ({
  containerMetadata,
  position,
}) => {
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    setExpanded(containerMetadata?.symbolic_mode === "expansion");
  }, [containerMetadata]);

  // Map/Default all props the sphere expects
  const sphereProps = {
    containerId: String(
      containerMetadata?.containerId ??
        containerMetadata?.id ??
        "unknown"
    ),
    active: Boolean(containerMetadata?.active ?? true),
    glyph: containerMetadata?.glyph ?? null,
    logicDepth: Number(containerMetadata?.logicDepth ?? 0),
    runtimeTick: Number(containerMetadata?.runtimeTick ?? 0),
    soulLocked: Boolean(containerMetadata?.soulLocked ?? false),

    // the ones you already have:
    position,
    expanded,
  };

  return <HobermanSphere {...sphereProps} />;
};

export default HobermanSphereController;
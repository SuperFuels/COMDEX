"use client";
import dynamic from "next/dynamic";
import React from "react";
import type { AtomModel, Vec3 } from "@/types/atom";

const AtomContainer = dynamic(() => import("../ContainerMap/AtomContainer"), { ssr: false });

interface Props {
  atom: AtomModel;
  position?: Vec3;
}

const AtomContainerWrapper: React.FC<Props> = ({ atom, position }) => {
  return <AtomContainer atom={atom} position={position} />;
};

export default AtomContainerWrapper;
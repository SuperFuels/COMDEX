"use client";

import dynamic from "next/dynamic";
import Shell from "@/components/Shell";

const PhotonAlgebraDemoTab = dynamic(() => import("../tabs/photon_algebra_demo"), {
  ssr: false,
});

export default function PhotonAlgebraDemoPage() {
  return (
    <Shell activeKey="photon-algebra-demo">
      <PhotonAlgebraDemoTab />
    </Shell>
  );
}
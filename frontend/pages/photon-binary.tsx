"use client";

import dynamic from "next/dynamic";
import Shell from "@/components/Shell";

const PhotonBinaryTab = dynamic(() => import("../tabs/photon-binary"), {
  ssr: false,
});

export default function PhotonBinaryPage() {
  return (
    <Shell activeKey="photon-binary">
      <PhotonBinaryTab />
    </Shell>
  );
}
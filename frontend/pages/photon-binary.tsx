// /workspaces/COMDEX/frontend/pages/photon-binary.tsx
"use client";

import dynamic from "next/dynamic";
import Shell from "@/components/Shell";

const PhotonBinaryTab = dynamic(() => import("@/tabs/photon-binary"), {
  ssr: false,
});

export default function PhotonBinaryPage() {
  return (
    <Shell activeKey="photon_binary">
      <PhotonBinaryTab />
    </Shell>
  );
}
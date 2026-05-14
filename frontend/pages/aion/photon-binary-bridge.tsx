// /workspaces/COMDEX/frontend/pages/aion/photon-binary-bridge.tsx
"use client";

import dynamic from "next/dynamic";
import Shell from "@/components/Shell";

export const getServerSideProps = async () => ({ props: {} });

// IMPORTANT: import the TAB (index), not the inner demo component.
const PhotonBinaryTab = dynamic(() => import("../../tabs/photon-binary"), { ssr: false });

export default function PhotonBinaryBridgePage() {
  return (
    <Shell activeKey="photon-binary">
      <PhotonBinaryTab />
    </Shell>
  );
}
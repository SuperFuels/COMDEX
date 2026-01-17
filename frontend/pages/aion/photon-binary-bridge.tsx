import React from "react";
import dynamic from "next/dynamic";

export const getServerSideProps = async () => ({ props: {} });

// dynamic import avoids any “window/three/animation” issues during build
const FullyHookedDemo = dynamic(
  () => import("../../components/demos/FullyHookedDemo"),
  { ssr: false }
);

export default function PhotonBinaryBridgePage() {
  return (
    <div className="p-6">
      <FullyHookedDemo />
    </div>
  );
}
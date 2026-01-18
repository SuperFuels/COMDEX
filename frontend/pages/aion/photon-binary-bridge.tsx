import dynamic from "next/dynamic";

const PhotonBinaryTab = dynamic(() => import("../../tabs/photon-binary"), {
  ssr: false,
});

export default function PhotonBinaryBridgePage() {
  return (
    <div className="p-6">
      <PhotonBinaryTab />
    </div>
  );
}
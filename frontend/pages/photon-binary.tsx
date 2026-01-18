import dynamic from "next/dynamic";

const PhotonBinaryTab = dynamic(() => import("../tabs/photon-binary"), {
  ssr: false,
});

export default function PhotonBinaryPage() {
  return <PhotonBinaryTab />;
}
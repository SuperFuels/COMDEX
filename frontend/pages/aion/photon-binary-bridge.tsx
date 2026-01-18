import dynamic from "next/dynamic";

export const getServerSideProps = async () => ({ props: {} });

// This is the real path you said you have:
const FullyHookedDemo = dynamic(
  () => import("../../tabs/photon-binary/FullyHookedDemo"),
  { ssr: false }
);

export default function PhotonBinaryBridgePage() {
  return (
    <div className="p-6">
      <FullyHookedDemo />
    </div>
  );
}
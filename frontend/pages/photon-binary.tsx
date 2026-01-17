import dynamic from "next/dynamic";

const PhotonBinaryTab = dynamic(() => import("../tabs/photon-binary"), {
  ssr: false,
});

export async function getServerSideProps() {
  return { props: {} };
}

export default function PhotonBinaryPage() {
  return <PhotonBinaryTab />;
}
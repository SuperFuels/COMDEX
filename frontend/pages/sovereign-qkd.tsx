import dynamic from "next/dynamic";

const SovereignQKDTab = dynamic(() => import("../tabs/sovereign-qkd"), { ssr: false });

export async function getServerSideProps() {
  return { props: {} };
}

export default function SovereignQKDPage() {
  return <SovereignQKDTab />;
}
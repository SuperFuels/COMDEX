import dynamic from "next/dynamic";

const Shell = dynamic(() => import("@/components/Shell"), { ssr: false });
const AionTab = dynamic(() => import("@/tabs/Aion"), { ssr: false });

export default function AionLabPage() {
  return (
    <Shell activeKey="aion">
      <AionTab />
    </Shell>
  );
}

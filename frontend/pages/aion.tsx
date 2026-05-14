// frontend/pages/aion.tsx
import dynamic from "next/dynamic";

const Shell = dynamic(() => import("@/components/Shell"), { ssr: false });
const AionTab = dynamic(() => import("@/tabs/Aion"), { ssr: false });

export default function AionPage() {
  return (
    <Shell activeKey="aion">
      <AionTab />
    </Shell>
  );
}
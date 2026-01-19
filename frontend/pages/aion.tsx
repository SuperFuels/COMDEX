// frontend/pages/aion.tsx
"use client";

import dynamic from "next/dynamic";
import Shell from "@/components/Shell";

const AionTab = dynamic(() => import("@/tabs/Aion"), { ssr: false });

export default function AionPage() {
  return (
    <Shell activeKey="aion">
      <AionTab />
    </Shell>
  );
}
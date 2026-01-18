"use client";

import dynamic from "next/dynamic";
import Shell from "@/components/Shell";

const SubstrateComparisonTab = dynamic(() => import("../tabs/substrate-comparison"), {
  ssr: false,
});

export default function SubstrateComparisonPage() {
  return (
    <Shell activeKey="substrate-comparison">
      <SubstrateComparisonTab />
    </Shell>
  );
}
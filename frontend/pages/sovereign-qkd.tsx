"use client";

import dynamic from "next/dynamic";
import Shell from "@/components/Shell";

const SovereignQKDTab = dynamic(() => import("../tabs/sovereign-qkd"), {
  ssr: false,
});

export default function SovereignQKDPage() {
  return (
    <Shell activeKey="sovereign-qkd">
      <SovereignQKDTab />
    </Shell>
  );
}
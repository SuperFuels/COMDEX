"use client";

import dynamic from "next/dynamic";
import Shell from "@/components/Shell";

const WirePackTab = dynamic(() => import("../tabs/WirePack"), { ssr: false });

export default function WirePackPage() {
  return (
    <Shell activeKey="wirepack">
      <WirePackTab />
    </Shell>
  );
}
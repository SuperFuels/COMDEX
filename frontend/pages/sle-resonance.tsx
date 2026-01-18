"use client";

import dynamic from "next/dynamic";
import Shell from "@/components/Shell";

const SLEResonanceTab = dynamic(() => import("../tabs/sle-resonance"), {
  ssr: false,
});

export default function SLEResonancePage() {
  return (
    <Shell activeKey="sle-resonance">
      <SLEResonanceTab />
    </Shell>
  );
}
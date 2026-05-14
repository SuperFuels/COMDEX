"use client";

import dynamic from "next/dynamic";
import Shell from "@/components/Shell";

const LaunchTab = dynamic(() => import("../tabs/launch"), { ssr: false });

export default function LaunchPage() {
  return (
    <Shell activeKey="launch">
      <LaunchTab />
    </Shell>
  );
}
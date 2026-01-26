// /workspaces/COMDEX/frontend/pages/launch.tsx
"use client";

import dynamic from "next/dynamic";
import Shell from "@/components/Shell";

const AionLaunchTab = dynamic(() => import("../tabs/launch"), { ssr: false });

export default function LaunchPage() {
  return (
    <Shell activeKey="launch">
      <AionLaunchTab />
    </Shell>
  );
}
// /workspaces/COMDEX/frontend/pages/rqc-awareness.tsx
"use client";

import dynamic from "next/dynamic";
import Shell from "@/components/Shell";

const RQCAwarenessTab = dynamic(() => import("@/tabs/RQCAwareness"), {
  ssr: false,
});

export default function RQCAwarenessPage() {
  return (
    <Shell activeKey="rqc_awareness">
      <RQCAwarenessTab />
    </Shell>
  );
}
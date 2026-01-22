"use client";

import dynamic from "next/dynamic";
import Shell from "@/components/Shell";

const QfcCanvasTab = dynamic(() => import("@/tabs/qfc-canvas"), {
  ssr: false,
});

export default function QfcCanvasPage() {
  return (
    <Shell activeKey="qfc_canvas">
      <QfcCanvasTab />
    </Shell>
  );
}
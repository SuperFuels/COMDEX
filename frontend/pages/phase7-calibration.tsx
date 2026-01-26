"use client";

import dynamic from "next/dynamic";
import Shell from "@/components/Shell";

const Phase7CalibrationTab = dynamic(
  () => import("../tabs/cognition/phase7-calibration"),
  { ssr: false }
);

export default function CognitionPage() {
  return (
    <Shell activeKey="phase7-calibration">
      <Phase7CalibrationTab />
    </Shell>
  );
}
"use client";

import Shell from "@/components/Shell";
import SQIDemo from "@/tabs/sqi/SQIDemo";

export default function SQIPage() {
  return (
    <Shell activeKey="sqi">
      <SQIDemo />
    </Shell>
  );
}